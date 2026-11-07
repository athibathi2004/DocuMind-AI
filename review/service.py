from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import selectinload, Session

from app.core.errors import DocumentNotFoundError, ReviewTaskNotFoundError
from app.models.document import Document, DocumentStatus
from app.models.extraction import ExtractedField, ValidationStatus
from app.models.review import (
    ReviewTask,
    ReviewHistory,
    ReviewStatus,
    ReviewActionType,
)


class ReviewService:
    """
    Manages Human-in-the-Loop (HITL) review tasks, manual corrections,
    approvals, rejections, and comprehensive audit history.
    """

    def get_review_queue(
        self,
        session: Session,
        status: Optional[ReviewStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ReviewTask]:
        """Fetch review queue items ordered by creation date."""
        stmt = (
            select(ReviewTask)
            .options(
                selectinload(ReviewTask.history),
                selectinload(ReviewTask.document),
            )
            .order_by(ReviewTask.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status:
            stmt = stmt.where(ReviewTask.status == status)

        result = session.execute(stmt)
        return list(result.scalars().all())

    def get_review_task(
        self, session: Session, review_id: str
    ) -> ReviewTask:
        """Retrieve a specific review task by ID."""
        stmt = (
            select(ReviewTask)
            .options(
                selectinload(ReviewTask.history),
                selectinload(ReviewTask.document).selectinload(Document.extracted_fields),
            )
            .where(ReviewTask.id == review_id)
        )
        result = session.execute(stmt)
        task = result.scalars().first()
        if not task:
            raise ReviewTaskNotFoundError(f"Review task '{review_id}' not found.")
        return task

    def update_field_value(
        self,
        session: Session,
        field_id: str,
        new_value: str,
        reviewer: str = "reviewer",
        notes: Optional[str] = None,
    ) -> ExtractedField:
        """
        Apply human manual override to an extracted field and record audit history.
        """
        stmt = select(ExtractedField).where(ExtractedField.id == field_id)
        res = session.execute(stmt)
        field = res.scalars().first()
        if not field:
            raise DocumentNotFoundError(f"Field with ID '{field_id}' not found.")

        old_val = field.field_value
        if not field.is_manual_override:
            field.original_value = old_val

        field.field_value = new_value
        field.normalized_value = new_value
        field.is_manual_override = True
        field.confidence = 1.0  # Human verified
        field.validation_status = ValidationStatus.VALID
        field.review_required = False

        # Find or create corresponding review task for history tracking
        task_stmt = select(ReviewTask).where(ReviewTask.document_id == field.document_id)
        task_res = session.execute(task_stmt)
        task = task_res.scalars().first()

        if task:
            history_entry = ReviewHistory(
                task_id=task.id,
                field_id=field.id,
                field_name=field.field_name,
                action=ReviewActionType.EDIT_FIELD,
                previous_value=old_val,
                new_value=new_value,
                reviewer=reviewer,
                notes=notes or f"Manual correction: '{old_val}' -> '{new_value}'",
            )
            session.add(history_entry)

        session.commit()
        session.refresh(field)
        return field

    def approve_review(
        self,
        session: Session,
        review_id: str,
        reviewer: str = "reviewer",
        notes: Optional[str] = None,
    ) -> ReviewTask:
        """Mark document review task as Approved and update document status to COMPLETED."""
        task = self.get_review_task(session, review_id)
        task.status = ReviewStatus.APPROVED
        task.reviewed_by = reviewer
        task.reviewer_notes = notes
        task.completed_at = datetime.now(timezone.utc)

        # Update parent document status
        doc_stmt = select(Document).where(Document.id == task.document_id)
        doc_res = session.execute(doc_stmt)
        doc = doc_res.scalars().first()
        if doc:
            doc.status = DocumentStatus.COMPLETED

        history_entry = ReviewHistory(
            task_id=task.id,
            action=ReviewActionType.APPROVE,
            reviewer=reviewer,
            notes=notes or "Document approved by human reviewer.",
        )
        session.add(history_entry)

        session.commit()
        session.refresh(task)
        return task

    def reject_review(
        self,
        session: Session,
        review_id: str,
        reviewer: str = "reviewer",
        notes: Optional[str] = None,
    ) -> ReviewTask:
        """Mark document review task as Rejected and update document status to REJECTED."""
        task = self.get_review_task(session, review_id)
        task.status = ReviewStatus.REJECTED
        task.reviewed_by = reviewer
        task.reviewer_notes = notes
        task.completed_at = datetime.now(timezone.utc)

        # Update parent document status
        doc_stmt = select(Document).where(Document.id == task.document_id)
        doc_res = session.execute(doc_stmt)
        doc = doc_res.scalars().first()
        if doc:
            doc.status = DocumentStatus.REJECTED

        history_entry = ReviewHistory(
            task_id=task.id,
            action=ReviewActionType.REJECT,
            reviewer=reviewer,
            notes=notes or "Document rejected by human reviewer.",
        )
        session.add(history_entry)

        session.commit()
        session.refresh(task)
        return task


review_service = ReviewService()

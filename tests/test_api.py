import io
import pytest


def test_api_health(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "DocuMind AI" in data["app_name"]


def test_api_document_upload_and_crud(client):
    file_content = b"%PDF-1.4 Mock PDF content for API test"
    files = {"file": ("api_test.pdf", io.BytesIO(file_content), "application/pdf")}

    # 1. Upload
    res_upload = client.post("/api/v1/documents/upload", files=files)
    assert res_upload.status_code == 201
    doc_data = res_upload.json()
    doc_id = doc_data["id"]
    assert doc_data["original_filename"] == "api_test.pdf"

    # 2. Get list
    res_list = client.get("/api/v1/documents")
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1

    # 3. Get document detail
    res_get = client.get(f"/api/v1/documents/{doc_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == doc_id

    # 4. Process document
    res_proc = client.post(f"/api/v1/documents/{doc_id}/process?ocr_provider=mock")
    assert res_proc.status_code == 200
    assert res_proc.json()["status"] in ["COMPLETED", "NEEDS_REVIEW"]

    # 5. Get OCR
    res_ocr = client.get(f"/api/v1/documents/{doc_id}/ocr")
    assert res_ocr.status_code == 200
    assert len(res_ocr.json()) >= 1

    # 6. Get Fields
    res_fields = client.get(f"/api/v1/documents/{doc_id}/fields")
    assert res_fields.status_code == 200
    fields = res_fields.json()
    assert len(fields) > 0

    # 7. Edit field
    target_field = fields[0]
    res_patch = client.patch(
        f"/api/v1/fields/{target_field['id']}",
        json={"field_value": "NEW_OVERRIDDEN_VALUE", "reviewer_notes": "API test edit"},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["field_value"] == "NEW_OVERRIDDEN_VALUE"

    # 8. Analytics Overview
    res_analytics = client.get("/api/v1/analytics/overview")
    assert res_analytics.status_code == 200
    assert res_analytics.json()["total_documents"] >= 1

    # 9. Delete document
    res_del = client.delete(f"/api/v1/documents/{doc_id}")
    assert res_del.status_code == 200

    # 10. Verify 404
    res_404 = client.get(f"/api/v1/documents/{doc_id}")
    assert res_404.status_code == 404


def test_api_duplicate_upload_409(client):
    content = b"Same bytes duplicate check API"
    files1 = {"file": ("file1.pdf", io.BytesIO(content), "application/pdf")}
    files2 = {"file": ("file2.pdf", io.BytesIO(content), "application/pdf")}

    res1 = client.post("/api/v1/documents/upload", files=files1)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/documents/upload", files=files2)
    assert res2.status_code == 409


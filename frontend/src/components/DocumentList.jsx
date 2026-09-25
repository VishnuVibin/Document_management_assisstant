import {
  deleteDocument,
  downloadDocument,
} from "../services/api";

function DocumentList({ documents, onDelete }) {

  const handleDelete = async (id) => {
    const confirmDelete = window.confirm(
      "Are you sure you want to delete this document?"
    );

    if (!confirmDelete) return;

    try {
      await deleteDocument(id);

      alert("Document deleted");

      onDelete();
    } catch (error) {
      console.error(error);
      alert("Failed to delete document");
    }
  };

  const handleDownload = async (document) => {
    try {
      await downloadDocument(
        document.id,
        document.filename
      );
    } catch (error) {
      console.error(error);
      alert("Download failed");
    }
  };

  return (
    <div className="documents">

      <h2>Uploaded Documents</h2>

      {documents.length === 0 ? (
        <p>No documents uploaded.</p>
      ) : (
        <div className="document-list">

          {documents.map((document) => (

            <div
              className="document-card"
              key={document.id}
            >

              <div>
                <h3>{document.filename}</h3>

                <p>
                  Uploaded:{" "}
                  {document.created_at || "Unknown"}
                </p>
              </div>

              <div className="document-actions">

                <button
                  onClick={() =>
                    handleDownload(document)
                  }
                >
                  Download
                </button>

                <button
                  className="delete-btn"
                  onClick={() =>
                    handleDelete(document.id)
                  }
                >
                  Delete
                </button>

              </div>

            </div>

          ))}

        </div>
      )}

    </div>
  );
}

export default DocumentList;
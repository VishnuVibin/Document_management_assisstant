import { useState } from "react";
import { uploadDocument } from "../services/api";

function UploadDocument({ onUpload }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleUpload = async () => {
    if (!file) {
      alert("Please select a file");
      return;
    }

    try {
      setLoading(true);

      await uploadDocument(file);

      alert("Document uploaded successfully");

      setFile(null);
      document.getElementById("fileInput").value = "";

      onUpload();
    } catch (error) {
      console.error(error);
      alert("Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload-box">
      <h2>Upload Document</h2>

      <input
        id="fileInput"
        type="file"
        onChange={(e) => setFile(e.target.files[0])}
      />

      {file && (
        <p>
          Selected: <strong>{file.name}</strong>
        </p>
      )}

      <button
        onClick={handleUpload}
        disabled={loading}
      >
        {loading ? "Uploading..." : "Upload"}
      </button>
    </div>
  );
}

export default UploadDocument;
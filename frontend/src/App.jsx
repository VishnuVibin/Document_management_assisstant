import { useEffect, useState } from "react";

import UploadDocument from "./components/UploadDocument";
import DocumentList from "./components/DocumentList";
import Chat from "./components/Chat";

import { getDocuments } from "./services/api";

import "./App.css";

function App() {

  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadDocuments = async () => {

    try {

      setLoading(true);

      const data = await getDocuments();

      setDocuments(
        data.documents || data || []
      );

    } catch (error) {

      console.error(error);

      alert("Failed to load documents");

    } finally {

      setLoading(false);

    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  return (
    <div className="app">

      <header className="header">

        <h1>Document AI Assistant</h1>

        <p>
          Upload documents and ask questions
          using AI.
        </p>

      </header>

      <main className="container">

        <section className="upload-section">

          <UploadDocument
            onUpload={loadDocuments}
          />

        </section>

        <section className="documents-section">

          {loading ? (
            <p>Loading documents...</p>
          ) : (
            <DocumentList
              documents={documents}
              onDelete={loadDocuments}
            />
          )}

        </section>

        <section className="chat-section">

          <Chat />

        </section>

      </main>

    </div>
  );
}

export default App;
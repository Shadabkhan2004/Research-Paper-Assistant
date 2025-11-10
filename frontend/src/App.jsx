import { useState } from "react";
import axios from "axios";
import { FiUpload, FiSend, FiFileText } from "react-icons/fi";

const API_BASE_URL = "https://research-paper-assistant-backend.onrender.com";

function App() {
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

const uploadPDF = async () => {
  if (!file) return alert("Select a PDF first!");
  setUploading(true);

  try {
    const formData = new FormData();
    formData.append("file", file);

    const res = await axios.post(`${API_BASE_URL}/upload-pdf/`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });

    if (res.data.message) {
      alert(res.data.message);
    } else if (res.data.error) {
      alert(`Upload failed: ${res.data.error}`);
    }

    setFile(null);
    document.getElementById("fileUpload").value = "";
  } catch (err) {
    console.error(err);
    alert(err.response?.data?.error || "Failed to upload PDF. Check backend logs.");
  } finally {
    setUploading(false);
  }
};


  const askQuestion = async () => {
    if (!query) return;
    setLoading(true);
    setAnswer("");
    try {
      const res = await axios.post(`${API_BASE_URL}/ask-question/`, { query });
      setAnswer(res.data.answer);
    } catch (err) {
      setAnswer("Failed to get answer. Check your backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-100 to-purple-200 p-8 flex flex-col items-center">
      <h1 className="text-5xl font-extrabold mb-10 text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-pink-600 drop-shadow-lg">
        📚 Research Paper Q&A
      </h1>

      {/* PDF Upload */}
      <div className="mb-8 w-full max-w-xl">
        <label 
          htmlFor="fileUpload"
          className="cursor-pointer flex flex-col items-center justify-center border-4 border-dashed border-purple-400 rounded-lg h-40 bg-white hover:bg-purple-50 transition-all duration-300">
          <FiUpload size={48} className="text-purple-500 mb-2"/>
          {file ? <p className="font-medium">{file.name}</p> : <p className="text-gray-500">Drag & drop a PDF here, or click to select</p>}
        </label>
        <input 
          type="file"
          id="fileUpload"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <button
          onClick={uploadPDF}
          disabled={uploading}
          className={`mt-4 w-full bg-purple-600 text-white py-3 rounded-lg font-semibold shadow-lg hover:bg-purple-700 transition-colors ${uploading ? "opacity-70 cursor-not-allowed" : ""}`}
        >
          {uploading ? "Uploading..." : "Upload PDF"}
        </button>
      </div>

      {/* Question Input */}
      <div className="mb-8 w-full max-w-xl flex flex-col">
        <div className="flex">
          <input
            type="text"
            placeholder="Ask a question..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 border border-gray-300 rounded-l-lg p-3 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent"
          />
          <button
            onClick={askQuestion}
            disabled={loading}
            className={`bg-green-500 text-white px-6 rounded-r-lg flex items-center justify-center hover:bg-green-600 transition-colors ${loading ? "opacity-70 cursor-not-allowed" : ""}`}
          >
            <FiSend className="mr-2"/> {loading ? "Thinking..." : "Ask"}
          </button>
        </div>
      </div>

      {/* Answer Box */}
      {answer && (
        <div className="bg-white p-6 rounded-2xl shadow-2xl w-full max-w-2xl animate-fadeIn border-l-4 border-purple-500">
          <h2 className="flex items-center text-2xl font-bold mb-4 text-purple-600">
            <FiFileText className="mr-2"/> Answer
          </h2>
          <p className="whitespace-pre-wrap text-gray-800">{answer}</p>
        </div>
      )}
    </div>
  );
}

export default App;

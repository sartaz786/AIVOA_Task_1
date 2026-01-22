import React, { useState } from "react";
import "./App.css"; // Ensure you have the CSS file I gave you earlier!

function App() {
  const [messages, setMessages] = useState([
    { sender: "ai", text: "Hello! I am your AI Assistant. Describe your interaction." },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    hcp_name: "",
    date: "",
    time: "",
    topics: "",
    sentiment: "Neutral",
    outcomes: "",
    interaction_type: "Meeting",
    attendees: "",
    follow_up_actions: ""
  });

  const sendMessage = async () => {
    if (!input.trim()) return;

    // 1. Show User Message
    const userMsg = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true); // START LOADING

    try {
      // 2. Send to Backend
      console.log("Sending to backend:", userMsg.text);
      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg.text }),
      });

      const data = await response.json();
      console.log("Received from backend:", data);

      // 3. Update Chat
      setMessages((prev) => [
        ...prev,
        { sender: "ai", text: data.reply || "Done." }
      ]);

      // 4. INSTANTLY FILL THE FORM
      if (data.updated_form) {
        console.log("Filling form with:", data.updated_form);
        setFormData(data.updated_form);
      }

    } catch (error) {
      console.error("Error:", error);
      setMessages((prev) => [
        ...prev,
        { sender: "ai", text: "Error: Could not connect to backend. Check terminal." }
      ]);
    } finally {
      setLoading(false); // STOP LOADING (Even if error)
    }
  };

  return (
    <div className="app-container">
      {/* LEFT SIDE: FORM */}
      <div className="form-panel">
        <h2>📄 Log HCP Interaction</h2>
        
        <div className="form-group">
          <label>HCP Name</label>
          <input type="text" value={formData.hcp_name || ""} readOnly placeholder="AI will fill this..." />
        </div>

        <div className="row">
          <div className="col form-group">
            <label>Date</label>
            <input type="text" value={formData.date || ""} readOnly />
          </div>
          <div className="col form-group">
            <label>Type</label>
            <input type="text" value={formData.interaction_type || ""} readOnly />
          </div>
        </div>

        <div className="form-group">
          <label>Topics Discussed</label>
          <textarea value={formData.topics || ""} readOnly />
        </div>

        <div className="form-group">
          <label>Observed Sentiment</label>
          <input type="text" value={formData.sentiment || ""} readOnly />
        </div>

        <div className="form-group">
          <label>Outcomes & Agreements</label>
          <textarea value={formData.outcomes || ""} readOnly />
        </div>
      </div>

      {/* RIGHT SIDE: CHAT */}
      <div className="chat-panel">
        <div className="chat-window">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.sender}`}>
              {msg.text}
            </div>
          ))}
          {loading && <div className="loading-bubble">AI is processing...</div>}
        </div>

        <div className="input-area">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Type here..."
          />
          <button onClick={sendMessage}>Send</button>
        </div>
      </div>
    </div>
  );
}

export default App;
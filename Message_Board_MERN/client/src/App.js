import React, { useState, useEffect } from 'react';

function App() {
  const [messages, setMessages] = useState([]);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    username: ''
  });

  useEffect(() => {
    fetchMessages();
  }, []);

  const fetchMessages = async () => {
    const response = await fetch('/api/messages');
    const data = await response.json();
    setMessages(data);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    await fetch('/api/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });
    fetchMessages();
    setFormData({ title: '', description: '', username: '' });
  };

  return (
    <div>
      <h1>Message Board</h1>
      
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Title"
          value={formData.title}
          onChange={(e) => setFormData({...formData, title: e.target.value})}
          required
        />
        <textarea
          placeholder="Description"
          value={formData.description}
          onChange={(e) => setFormData({...formData, description: e.target.value})}
          required
        />
        <input
          type="text"
          placeholder="Username"
          value={formData.username}
          onChange={(e) => setFormData({...formData, username: e.target.value})}
          required
        />
        <button type="submit">Post Message</button>
      </form>

      <div>
        {messages.map(message => (
          <div key={message._id}>
            <h3>{message.title}</h3>
            <p>{message.description}</p>
            <small>By {message.username}</small>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
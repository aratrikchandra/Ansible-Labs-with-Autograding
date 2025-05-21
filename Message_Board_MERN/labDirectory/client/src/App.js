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
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      <h1 style={{ textAlign: 'center', color: '#2c3e50' }}>Message Board</h1>
      
      <form 
        onSubmit={handleSubmit}
        style={{ 
          display: 'flex',
          flexDirection: 'column',
          gap: '15px',
          marginBottom: '40px',
          background: '#f8f9fa',
          padding: '20px',
          borderRadius: '8px'
        }}
      >
        <input
          style={inputStyle}
          type="text"
          placeholder="Title"
          value={formData.title}
          onChange={(e) => setFormData({...formData, title: e.target.value})}
          required
        />
        <textarea
          style={{ ...inputStyle, height: '80px' }}
          placeholder="Description"
          value={formData.description}
          onChange={(e) => setFormData({...formData, description: e.target.value})}
          required
        />
        <input
          style={inputStyle}
          type="text"
          placeholder="Username"
          value={formData.username}
          onChange={(e) => setFormData({...formData, username: e.target.value})}
          required
        />
        <button 
          type="submit"
          style={{
            padding: '10px 20px',
            background: '#3498db',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '16px'
          }}
        >
          Post Message
        </button>
      </form>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {messages.map(message => (
          <div 
            key={message._id}
            style={{
              background: '#ffffff',
              borderRadius: '8px',
              padding: '20px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              borderLeft: '4px solid #3498db'
            }}
          >
            <h3 style={{ margin: '0 0 10px 0', color: '#2c3e50' }}>{message.title}</h3>
            <p style={{ margin: '0 0 10px 0', color: '#7f8c8d' }}>{message.description}</p>
            <small style={{ color: '#95a5a6', fontSize: '0.9em' }}>
              By {message.username}
            </small>
          </div>
        ))}
      </div>
    </div>
  );
}

const inputStyle = {
  padding: '10px',
  border: '1px solid #bdc3c7',
  borderRadius: '4px',
  fontSize: '16px',
  outline: 'none',
  transition: 'border-color 0.3s',
};

export default App;
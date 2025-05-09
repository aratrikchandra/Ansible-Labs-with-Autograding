import React, { useEffect, useState } from 'react';

function App() {
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetch('/api')
      .then(res => res.text())
      .then(data => setMessage(data))
      .catch(console.error);
  }, []);

  return (
    <div>
      <h1>React Frontend</h1>
      <p>Backend Response: {message}</p>
    </div>
  );
}

export default App;
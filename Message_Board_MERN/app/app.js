const express = require('express');
const bodyParser = require('body-parser');
const { MongoClient } = require('mongodb');

const app = express();
const PORT = 5000;
const DB_NAME = 'messageDB';
const DB_URL = 'mongodb://localhost:27017';

app.use(bodyParser.json());

// Connect to MongoDB
let db;
async function connectDB() {
  const client = new MongoClient(DB_URL);
  await client.connect();
  db = client.db(DB_NAME);
  console.log('Connected to MongoDB');
}
connectDB();

// Routes
app.get('/api/messages', async (req, res) => {
  try {
    const messages = await db.collection('messages').find().toArray();
    res.json(messages);
  } catch (err) {
    res.status(500).send(err.message);
  }
});

app.post('/api/messages', async (req, res) => {
  try {
    const { title, description, username } = req.body;
    const result = await db.collection('messages').insertOne({
      title,
      description,
      username,
      createdAt: new Date()
    });
    res.status(201).json(result.ops[0]);
  } catch (err) {
    res.status(400).send(err.message);
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
// backend/server.js
const express = require('express');
const cors = require('cors');
const app = express();
const PORT = 5001;

app.use(cors());
app.use(express.json());

// Mock Database (Pretend this is MongoDB)
const mockCompanies = [
    { id: 1, name: "AlgoUniversity", valuation: "$10M", sector: "EdTech" },
    { id: 2, name: "Stripe", valuation: "$95B", sector: "FinTech" }
];

// Tool Endpoint: The AI Agent calls this!
app.get('/api/companies', (req, res) => {
    res.json({ status: "success", data: mockCompanies });
});

// Tool Endpoint: Get specific company details
app.get('/api/companies/:id', (req, res) => {
    const company = mockCompanies.find(c => c.id === parseInt(req.params.id));
    res.json({ status: "success", data: company || {} });
});

app.listen(PORT, () => {
    console.log(`🛠️ Tool Backend running on port ${PORT}`);
});
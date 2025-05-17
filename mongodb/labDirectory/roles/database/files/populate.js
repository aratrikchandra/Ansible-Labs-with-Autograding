
// Remove all data from the collections
db.Users.deleteMany({});

// Users collection
db.Users.insertMany([
    { user_id: 1, name: "Alice Johnson", email: "alice.johnson@example.com" },
    { user_id: 2, name: "Bob Smith", email: "bob.smith@example.com" },
    { user_id: 3, name: "Charlie Brown", email: "charlie.brown@example.com" },
    { user_id: 4, name: "David Wilson", email: "david.wilson@example.com" },
    { user_id: 5, name: "Eva Adams", email: "eva.adams@example.com" },
    { user_id: 6, name: "Frank Miller", email: "frank.miller@example.com" },
    { user_id: 7, name: "Grace Lee", email: "grace.lee@example.com" },
    { user_id: 8, name: "Hannah Davis", email: "hannah.davis@example.com" },
    { user_id: 9, name: "Ian Thompson", email: "ian.thompson@example.com" },
    { user_id: 10, name: "Jack White", email: "jack.white@example.com" },
    { user_id: 11, name: "Karen Martinez", email: "karen.martinez@example.com" },
    { user_id: 12, name: "Liam Clark", email: "liam.clark@example.com" },
    { user_id: 13, name: "Mia Lopez", email: "mia.lopez@example.com" },
    { user_id: 14, name: "Noah Gonzalez", email: "noah.gonzalez@example.com" },
    { user_id: 15, name: "Olivia Harris", email: "olivia.harris@example.com" },
    { user_id: 16, name: "Paul Martin", email: "paul.martin@example.com" },
    { user_id: 17, name: "Quinn Walker", email: "quinn.walker@example.com" },
    { user_id: 18, name: "Rachel Lewis", email: "rachel.lewis@example.com" },
    { user_id: 19, name: "Sam Young", email: "sam.young@example.com" },
    { user_id: 20, name: "Tina King", email: "tina.king@example.com" }
]);

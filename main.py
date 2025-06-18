import os
import logging
from app import app, db
import routes  # Import routes to register them with the app

# Configure logging for production
logging.basicConfig(level=logging.INFO)

# Ensure all models are imported for database table creation
import models

# Create database tables
with app.app_context():
    try:
        db.create_all()
        logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Database initialization error: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

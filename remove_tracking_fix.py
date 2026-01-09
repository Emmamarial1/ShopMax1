import os
from app import app, db

def remove_tracking_fix():
    print("🔄 REMOVING TRACKING COLUMNS AND RESETTING DATABASE")
    
    # Delete the database file
    if os.path.exists('shopmax.db'):
        os.remove('shopmax.db')
        print("🗑️  Deleted old database")
    
    # Delete migrations folder if it exists
    if os.path.exists('migrations'):
        import shutil
        shutil.rmtree('migrations')
        print("🗑️  Deleted migrations folder")
    
    with app.app_context():
        # Create all tables with the simplified Order model
        db.create_all()
        print("✅ Created new database without tracking columns")
        
        # Initialize your data
        from app import create_admin_user, initialize_delivery_persons, create_sample_products
        create_admin_user()
        initialize_delivery_persons()
        create_sample_products()
        
        print("🎉 Database reset completed without tracking columns!")
        print("👉 The admin dashboard should now work!")

if __name__ == '__main__':
    remove_tracking_fix()
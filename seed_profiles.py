from database import SessionLocal, Profile, init_db
import os

def seed():
    init_db()
    db = SessionLocal()

    if db.query(Profile).count() > 0:
        print("Profiles already exist in database.")
        db.close()
        return

    sample_profiles = [
        Profile(name="Thoibi", age=23, marital_status="Single", country="India", hobbies="Dance, Reading", image_path="images/Thoibi.jpeg"),
        Profile(name="Payal", age=25, marital_status="Single", country="India", hobbies="Music, Photography", image_path="images/payal.jpg"),
        Profile(name="Preeti", age=24, marital_status="Single", country="India", hobbies="Cooking, Travel", image_path="images/preeti.jpg"),
        Profile(name="Riya", age=22, marital_status="Single", country="India", hobbies="Art, Fitness", image_path="images/riya.jpg"),
        Profile(name="Sofia", age=26, marital_status="Single", country="India", hobbies="Fashion, Movies", image_path="images/sofia.jpg"),
    ]

    db.add_all(sample_profiles)
    db.commit()
    print("Database successfully seeded with profiles!")
    db.close()

if __name__ == "__main__":
    seed()

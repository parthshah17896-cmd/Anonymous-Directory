from database import SessionLocal, Profile, init_db

def seed():
    init_db()
    db = SessionLocal()

    if db.query(Profile).count() > 0:
        print("Profiles already exist in database.")
        db.close()
        return

    sample_profiles = [
        Profile(
            name="Thoibi", age=23, marital_status="Single", country="India",
            hobbies="Dance, Reading", image_path="images/Thoibi.jpeg",
            bot_username="ChatWithThoibiBot"
        ),
        Profile(
            name="Payal", age=25, marital_status="Single", country="India",
            hobbies="Music, Photography", image_path="images/payal.jpg",
            bot_username="ChatWithPayalBot"
        ),
        Profile(
            name="Preeti", age=24, marital_status="Single", country="India",
            hobbies="Cooking, Travel", image_path="images/preeti.jpg",
            bot_username="ChatWithPreetiBot"
        ),
        Profile(
            name="Riya", age=22, marital_status="Single", country="India",
            hobbies="Art, Fitness", image_path="images/riya.jpg",
            bot_username="ChatWithRiyaaBot"
        ),
        Profile(
            name="Sofia", age=26, marital_status="Single", country="India",
            hobbies="Fashion, Movies", image_path="images/sofia.jpg",
            bot_username="Chatwithsofiaabot"
        ),
    ]

    db.add_all(sample_profiles)
    db.commit()
    print("Database successfully seeded with profiles and bot links!")
    db.close()

if __name__ == "__main__":
    seed()

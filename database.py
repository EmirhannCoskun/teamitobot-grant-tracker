"""
Database models and operations
"""
from sqlalchemy import create_engine, Column, Integer, BigInteger, String, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from sqlalchemy import BigInteger
import pytz
from config import config

TURKEY_TZ = pytz.timezone('Europe/Istanbul')
Base = declarative_base()

# ==========================================
# DATABASE MODELS
# ==========================================

class User(Base):
    """User model - stores Telegram users"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_subscribed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(TURKEY_TZ))
    
    # Relationships
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User chat_id={self.chat_id}>"


class Grant(Base):
    """Grant model - stores detected grants"""
    __tablename__ = "grants"
    
    id = Column(Integer, primary_key=True)
    text = Column(String(1000), unique=True, nullable=False)
    detected_at = Column(DateTime, default=lambda: datetime.now(TURKEY_TZ), index=True)
    
    # Relationships
    notifications = relationship("Notification", back_populates="grant", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Grant id={self.id}>"


class Notification(Base):
    """Notification model - tracks sent notifications"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    grant_id = Column(Integer, ForeignKey("grants.id"), nullable=False)
    sent_at = Column(DateTime, default=lambda: datetime.now(TURKEY_TZ))
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    grant = relationship("Grant", back_populates="notifications")


class Stats(Base):
    """Stats model - bot statistics"""
    __tablename__ = "stats"
    
    id = Column(Integer, primary_key=True)
    total_scrapes = Column(Integer, default=0)
    total_notifications = Column(Integer, default=0)
    total_users = Column(Integer, default=0)
    started_at = Column(DateTime, default=lambda: datetime.now(TURKEY_TZ))
    last_scrape_at = Column(DateTime, nullable=True)


# ==========================================
# DATABASE SETUP
# ==========================================

engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized")


def get_db():
    """Get database session"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ==========================================
# DATABASE OPERATIONS
# ==========================================

class DB:
    """Database operations - static methods"""
    
    # ========== USER OPERATIONS ==========
    
    @staticmethod
    def add_or_get_user(chat_id: int, username: str = None) -> User:
        """Add new user or get existing"""
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.chat_id == chat_id).first()
            if user:
                return user
            
            user = User(chat_id=chat_id, username=username)
            session.add(user)
            session.commit()
            print(f"✅ New user added: {chat_id}")
            return user
        finally:
            session.close()
    
    @staticmethod
    def get_user(chat_id: int) -> User:
        """Get user by chat_id"""
        session = SessionLocal()
        try:
            return session.query(User).filter(User.chat_id == chat_id).first()
        finally:
            session.close()
    
    @staticmethod
    def subscribe_user(chat_id: int) -> bool:
        """Subscribe user. Returns True only when subscription changes."""
        session = SessionLocal()

        try:
            user = session.query(User).filter(
                User.chat_id == chat_id
            ).first()

            if not user:
                return False

            if user.is_subscribed:
                return False

            user.is_subscribed = True
            session.commit()

            return True

        finally:
            session.close()

    @staticmethod
    def unsubscribe_user(chat_id: int) -> bool:
        """Unsubscribe user. Returns True only when subscription changes."""
        session = SessionLocal()

        try:
            user = session.query(User).filter(
                User.chat_id == chat_id
            ).first()

            if not user:
                return False

            if not user.is_subscribed:
                return False

            user.is_subscribed = False
            session.commit()

            return True

        finally:
            session.close()
    
    @staticmethod
    def get_subscribed_users() -> list:
        """Get all subscribed users"""
        session = SessionLocal()
        try:
            users = session.query(User).filter(
                User.is_subscribed == True,
                User.is_active == True
            ).all()
            return [user.chat_id for user in users]
        finally:
            session.close()
    
    @staticmethod
    def is_subscribed(chat_id: int) -> bool:
        """Check if user is subscribed"""
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.chat_id == chat_id).first()
            return user.is_subscribed if user else False
        finally:
            session.close()
    
    # ========== GRANT OPERATIONS ==========
    
    @staticmethod
    def add_grant(text: str) -> Grant:
        """Add grant to database"""
        session = SessionLocal()
        try:
            existing = session.query(Grant).filter(Grant.text == text).first()
            if existing:
                return existing
            
            grant = Grant(text=text)
            session.add(grant)
            session.commit()
            return grant
        finally:
            session.close()
    
    @staticmethod
    def get_all_grants() -> list:
        """Get all grants"""
        session = SessionLocal()
        try:
            return session.query(Grant).all()
        finally:
            session.close()
    
    # ========== NOTIFICATION OPERATIONS ==========
    
    @staticmethod
    def add_notification(chat_id: int, grant_id: int) -> bool:
        """Record notification"""
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.chat_id == chat_id).first()
            if not user:
                return False
            
            # Check if already sent
            existing = session.query(Notification).filter(
                Notification.user_id == user.id,
                Notification.grant_id == grant_id
            ).first()
            
            if existing:
                return False
            
            notification = Notification(user_id=user.id, grant_id=grant_id)
            session.add(notification)
            session.commit()
            return True
        finally:
            session.close()
    
    @staticmethod
    def get_user_notification_count(chat_id: int) -> int:
        """Get notification count for user"""
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.chat_id == chat_id).first()
            if not user:
                return 0
            return session.query(Notification).filter(Notification.user_id == user.id).count()
        finally:
            session.close()
    
    # ========== STATS OPERATIONS ==========
    
    @staticmethod
    def get_or_create_stats() -> Stats:
        """Get or create stats"""
        session = SessionLocal()
        try:
            stats = session.query(Stats).first()
            if not stats:
                stats = Stats()
                session.add(stats)
                session.commit()
            return stats
        finally:
            session.close()
    
    @staticmethod
    def increment_scrapes():
        """Increment scrape counter and record the time of this scrape"""
        session = SessionLocal()
        try:
            stats = session.query(Stats).first()
            if stats:
                stats.total_scrapes += 1
                stats.last_scrape_at = datetime.now(TURKEY_TZ)
                session.commit()
        finally:
            session.close()
    
    @staticmethod
    def increment_notifications():
        """Increment notification counter"""
        session = SessionLocal()
        try:
            stats = session.query(Stats).first()
            if stats:
                stats.total_notifications += 1
                session.commit()
        finally:
            session.close()
    
    @staticmethod
    def update_user_count():
        """Update user count"""
        session = SessionLocal()
        try:
            stats = session.query(Stats).first()
            count = session.query(User).filter(User.is_active == True).count()
            if stats:
                stats.total_users = count
                session.commit()
        finally:
            session.close()
    
    @staticmethod
    def get_stats_dict() -> dict:
        """Get stats as dictionary"""
        session = SessionLocal()
        try:
            stats = session.query(Stats).first()
            if not stats:
                return {
                    "scrapes": 0,
                    "notifications": 0,
                    "users": 0,
                    "started": None,
                    "last_scrape": None,
                }
            return {
                "scrapes": stats.total_scrapes,
                "notifications": stats.total_notifications,
                "users": stats.total_users,
                "started": stats.started_at,
                "last_scrape": stats.last_scrape_at,
            }
        finally:
            session.close()

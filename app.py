from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from sqlalchemy import Column, Integer, String, ForeignKey, create_engine, DateTime
from sqlalchemy.orm import relationship, Session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import datetime
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
import jwt
import datetime
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv

load_dotenv()

# SQLAlchemy setup
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost/socialmedia")
Base = declarative_base()
# Database Session
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Create tables
try:
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")  # Add a success message
except Exception as e:
    print(f"Error creating tables: {e}")  # Print any error during table creation
# FastAPI app
app = FastAPI()
# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "mysecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
# OAuth2 Password flow
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Models
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    posts = relationship("Post", back_populates="owner")
    comments = relationship("Comment", back_populates="user")
    likes = relationship("Like", back_populates="user")
class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    owner = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post")
    likes = relationship("Like", back_populates="post")
class Comment(Base):
    __tablename__ = 'comments'
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    post_id = Column(Integer, ForeignKey('posts.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")
class Like(Base):
    __tablename__ = 'likes'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    post_id = Column(Integer, ForeignKey('posts.id'))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship("User", back_populates="likes")
    post = relationship("Post", back_populates="likes")
# Votes table for "like" feature
from sqlalchemy import Table, MetaData
metadata = MetaData()
votes = Table(
    "votes",
    metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("post_id", Integer, ForeignKey("posts.id"), primary_key=True),
)
# Schemas
class UserBase(BaseModel):
    username: str
    email: str
class UserCreate(UserBase):
    password: str
class UserInDB(UserBase):
    id: int
    created_at: datetime.datetime
    class Config:
        orm_mode = True
class PostCreate(BaseModel):
    title: str
    content: str
class PostOut(BaseModel):
    id: int
    title: str
    content: str
    user_id: int
    created_at: datetime.datetime
    class Config:
        orm_mode = True
class CommentCreate(BaseModel):
    content: str
    post_id: int
class CommentOut(BaseModel):
    id: int
    content: str
    post_id: int
    user_id: int
    created_at: datetime.datetime
    class Config:
        orm_mode = True
class LikeOut(BaseModel):  # Schema for likes
    user_id: int
    post_id: int
    created_at: datetime.datetime
    class Config:
        orm_mode = True
# Utility functions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# Password hashing utilities
def get_password_hash(password: str):
    return pwd_context.hash(password)
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)
# JWT utility functions
def create_access_token(data: dict, expires_delta: datetime.timedelta = None):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + (
        expires_delta or datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    to_encode["sub"] = str(to_encode["sub"])  # Ensure the sub is a string
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
def verify_token(token: str) -> Optional[dict]:  # Change return type to Optional[dict]
    """
    Verifies the JWT token and returns the payload if valid, None otherwise.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError as e:
        print(f"JWT Decode Error: {e}")  # Log the specific error
        return None
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise credentials_exception
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user
# User routes
@app.post("/register", response_model=UserInDB)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        created_at=datetime.datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if user is None or not verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials"
        )
    access_token = create_access_token(data={"sub": str(user.id)})  # Ensure sub is string
    return {"access_token": access_token, "token_type": "bearer"}
# Post routes (CRUD operations)
posts_router = APIRouter()
@posts_router.post("/", response_model=PostOut)
def create_post(
    post: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_post = Post(title=post.title, content=post.content, user_id=current_user.id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post
@posts_router.get("/{post_id}", response_model=PostOut)
def read_post(post_id: int, db: Session = Depends(get_db)):
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if db_post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    return db_post
@posts_router.get("/", response_model=List[PostOut])
def list_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).all()
    return posts
@posts_router.put("/{post_id}", response_model=PostOut)
def update_post(
    post_id: int,
    post: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if db_post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    if db_post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post",
        )
    db_post.title = post.title
    db_post.content = post.content
    db.commit()
    db.refresh(db_post)
    return db_post
@posts_router.delete("/{post_id}")
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_post = db.query(Post).filter(Post.id == post_id).first()
    if db_post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    if db_post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post",
        )
    db.delete(db_post)
    db.commit()
    return {"detail": "Post deleted successfully"}
app.include_router(posts_router, prefix="/posts", tags=["posts"])

from sqlalchemy import func

@posts_router.get("/with_likes", response_model=List[PostOut])
def list_posts_with_likes(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10,
):
    posts_with_likes = (
        db.query(
            Post,
            func.count(Like.id).label("likes_count")
        )
        .outerjoin(Like, Like.post_id == Post.id)
        .group_by(Post.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    # Return posts only, likes_count can be added to response model if needed
    return [post for post, likes_count in posts_with_likes]

# Likes routes
likes_router = APIRouter()
@likes_router.post("/{post_id}/likes", response_model=LikeOut, status_code=status.HTTP_201_CREATED)
def create_like(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    existing_like = db.query(Like).filter(Like.user_id == current_user.id, Like.post_id == post_id).first()
    if existing_like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You have already liked this post"
        )
    new_like = Like(user_id=current_user.id, post_id=post_id)
    db.add(new_like)
    db.commit()
    db.refresh(new_like)
    return new_like
@likes_router.delete("/{post_id}/likes", status_code=status.HTTP_200_OK)
def delete_like(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    existing_like = db.query(Like).filter(Like.user_id == current_user.id, Like.post_id == post_id).first()
    if not existing_like:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="You have not liked this post"
        )
    db.delete(existing_like)
    db.commit()
    return {"detail": "Like deleted successfully"}
app.include_router(likes_router, prefix="/posts", tags=["likes"])

comments_router = APIRouter()

@comments_router.post("/", response_model=CommentOut)
def create_comment(
    comment: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(Post).filter(Post.id == comment.post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    db_comment = Comment(
        content=comment.content,
        post_id=comment.post_id,
        user_id=current_user.id,
        created_at=datetime.datetime.utcnow()
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

@comments_router.get("/{comment_id}", response_model=CommentOut)
def read_comment(comment_id: int, db: Session = Depends(get_db)):
    db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if db_comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )
    return db_comment

@comments_router.get("/", response_model=List[CommentOut])
def list_comments(db: Session = Depends(get_db)):
    comments = db.query(Comment).all()
    return comments

@comments_router.put("/{comment_id}", response_model=CommentOut)
def update_comment(
    comment_id: int,
    comment: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if db_comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )
    if db_comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this comment",
        )
    db_comment.content = comment.content
    db.commit()
    db.refresh(db_comment)
    return db_comment

@comments_router.delete("/{comment_id}")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if db_comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )
    if db_comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this comment",
        )
    db.delete(db_comment)
    db.commit()
    return {"detail": "Comment deleted successfully"}

app.include_router(comments_router, prefix="/comments", tags=["comments"])

@app.get("/")
def home():
    return {"msg": "Hello, World!"}

from sqlalchemy import create_engine, Column, Integer, String, Boolean
from datetime import timedelta
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import DateTime
from datetime import datetime
from src.logger_config import get_logger

# Database setup
# Ensure the data directory exist
import os
os.makedirs("data", exist_ok=True)

engine = create_engine('sqlite:///data/file_tracker.db') 

class Base(DeclarativeBase):
    pass

class FileToDownload(Base):
    __tablename__ = 'files_to_download'
    id = Column(Integer, primary_key=True)
    filename = Column(String, unique=True, nullable=False)
    last_modified = Column(DateTime, nullable=False)
    downloaded = Column(Boolean, default=False) 
    download_location = Column(String, nullable=True)
    unpacked = Column(Boolean, default=None)
    unpacked_location = Column(String, nullable=True)
    removed = Column(Boolean, default=None)  # New field

    def __repr__(self):
        return f"<FileToDownload(id={self.id}, filename='{self.filename}', downloaded={self.downloaded}, unpacked={self.unpacked}, removed={self.removed})>"

Base.metadata.create_all(engine) 
Session = sessionmaker(bind=engine)

logger = get_logger(__name__)

# Object-oriented approach
class FileTracker:
    def __init__(self):
        self.session = Session()

    def add_file_to_track(self, filename, last_modified):       
        existing_file = self.session.query(FileToDownload).filter_by(filename=filename).first()
        if not existing_file:
            new_file = FileToDownload(filename=filename, last_modified=last_modified)
            self.session.add(new_file)
            logger.info(f"Added {filename} to the tracker")
        self.session.commit()

    def mark_file_as_downloaded(self, filename, download_location):
        """Marks a file as downloaded in the database."""
        file_to_update = self.session.query(FileToDownload).filter_by(filename=filename).first()
        if file_to_update:
            file_to_update.downloaded = True
            file_to_update.download_location = download_location
            self.session.commit()

    def mark_file_as_unpacked(self, filename, unpacked_folder):
        """Marks a file as unpacked in the database."""
        file_to_update = self.session.query(FileToDownload).filter_by(filename=filename).first()
        if file_to_update:
            file_to_update.unpacked = True
            file_to_update.unpacked_location = unpacked_folder
            file_to_update.removed = False
            self.session.commit()

    def mark_file_as_added_to_db(self, filename):
        """Marks a file as added to the database."""
        file_to_update = self.session.query(FileToDownload).filter_by(filename=filename).first()
        if file_to_update:
            file_to_update.added_to_db = True
            self.session.commit()

    def filter_not_downloaded(self, list_of_files):
        """Returns items from the input list that haven't been downloaded yet."""
        downloaded_files = self.session.query(FileToDownload.filename).filter_by(downloaded=True).all()
        downloaded_filenames = {file[0] for file in downloaded_files}
        return [file for file in list_of_files if file not in downloaded_filenames]

    def filter_not_unpacked(self, list_of_files):
        """Returns items from the input list that haven't been unpacked yet."""
        unpacked_files = self.session.query(FileToDownload.filename).filter_by(unpacked=True).all()
        unpacked_filenames = {file[0] for file in unpacked_files}
        return [file for file in list_of_files if file not in unpacked_filenames]
    
    def filter_not_added_to_db(self, list_of_files):
        """Returns items from the input list that haven't been added to the database yet."""
        added_to_db_files = self.session.query(FileToDownload.filename).filter_by(added_to_db=True).all()
        added_to_db_filenames = {file[0] for file in added_to_db_files}
        return [file for file in list_of_files if file not in added_to_db_filenames]

    def get_older_available_files(self):
        """Returns all files that are unpacked and not removed, excluding the 6 most recent."""
        recent_files = self.get_recent_available_files(limit=6)
        recent_ids = [file.id for file in recent_files]
        
        files = self.session.query(FileToDownload)\
            .filter_by(unpacked=True, removed=False)\
            .filter(~FileToDownload.id.in_(recent_ids))\
            .order_by(FileToDownload.last_modified.desc())\
            .all()
        return files

    def mark_file_as_removed(self, filename):
        """Marks a file as removed in the database."""
        file_to_update = self.session.query(FileToDownload).filter_by(filename=filename).first()
        if file_to_update:
            file_to_update.removed = True
            self.session.commit()

    def get_recent_available_files(self, limit=6):
        """Returns the most recent files that haven't been removed."""
        files = self.session.query(FileToDownload)\
            .filter_by(removed=False)\
            .order_by(FileToDownload.last_modified.desc())\
            .limit(limit)\
            .all()
        return files

    def close_session(self):
        """Closes the database session."""
        self.session.close()

    
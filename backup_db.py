#!/usr/bin/env python3
"""APEX Database Backup Script - Automated daily backups"""
import shutil
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APEX_DIR = Path("/home/aarav/Aarav/Autopilot")
DATA_DIR = APEX_DIR / "data"
BACKUP_DIR = APEX_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def backup_database():
    """Create timestamped backup of all databases."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / timestamp
    backup_path.mkdir(exist_ok=True)
    
    db_files = list(DATA_DIR.glob("*.db"))
    
    if not db_files:
        logger.warning("No database files found in %s", DATA_DIR)
        return
    
    for db_file in db_files:
        dest = backup_path / db_file.name
        shutil.copy2(db_file, dest)
        logger.info("Backed up %s -> %s", db_file, dest)
    
    # Create latest symlink
    latest = BACKUP_DIR / "latest"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(backup_path)
    
    # Cleanup old backups (keep last 30 days)
    cleanup_old_backups()
    
    logger.info("Backup complete: %s", backup_path)

def cleanup_old_backups(days: int = 30):
    """Remove backups older than specified days."""
    cutoff = datetime.utcnow().timestamp() - (days * 86400)
    
    for backup in BACKUP_DIR.iterdir():
        if backup.is_dir() and backup.name != "latest":
            if backup.stat().st_mtime < cutoff:
                shutil.rmtree(backup)
                logger.info("Removed old backup: %s", backup)

if __name__ == "__main__":
    backup_database()

#!/usr/bin/env python3

"""
Upload all chunks to Pinecone with smart time estimation.
Shows progress bar, elapsed time, and estimated completion time.
"""
import sys
import json
import os
import re
from pathlib import Path
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ingestion.load_data import load_data
from ingestion.create_chunks import create_chunks
from ingestion.upload_pinecone import upsert_chunks_to_pinecone

BATCH_SIZE = 100  # Upload in batches
CHECKPOINT_FILE = Path(__file__).with_name("upload_checkpoint.json")
LOG_FILE = Path(__file__).with_name("upload_progress.log")

def format_time(seconds):
    """Format seconds to HH:MM:SS"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.0f}m {seconds%60:.0f}s"
    else:
        hours = seconds / 3600
        minutes = (seconds % 3600) / 60
        return f"{hours:.0f}h {minutes:.0f}m"


def read_checkpoint() -> int:
    if not CHECKPOINT_FILE.exists():
        return 0

    try:
        with CHECKPOINT_FILE.open("r", encoding="utf-8") as handle:
            checkpoint = json.load(handle)
        return int(checkpoint.get("last_completed_batch", 0))
    except Exception:
        return 0


def read_log_checkpoint() -> int:
    if not LOG_FILE.exists():
        return 0

    try:
        pattern = re.compile(r"Batch\s+(\d+)\/(\d+):.*✓")
        last_completed_batch = 0
        with LOG_FILE.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                match = pattern.search(line)
                if match:
                    last_completed_batch = max(last_completed_batch, int(match.group(1)))
        return last_completed_batch
    except Exception:
        return 0


def get_start_batch(total_batches: int) -> int:
    resume_from = os.getenv("RESUME_FROM_BATCH")
    if resume_from:
        try:
            batch_number = int(resume_from)
            if batch_number > 0:
                return min(batch_number, total_batches)
        except ValueError:
            pass

    last_completed_batch = max(read_checkpoint(), read_log_checkpoint())
    if last_completed_batch <= 0:
        return 1
    return min(last_completed_batch + 1, total_batches)


def save_checkpoint(last_completed_batch: int, total_batches: int, total_uploaded: int) -> None:
    checkpoint = {
        "last_completed_batch": last_completed_batch,
        "total_batches": total_batches,
        "total_uploaded": total_uploaded,
        "updated_at": time.time(),
    }
    with CHECKPOINT_FILE.open("w", encoding="utf-8") as handle:
        json.dump(checkpoint, handle, indent=2)

print("=" * 80)
print("FULL DATASET UPLOAD WITH TIME ESTIMATION")
print("=" * 80)

try:
    print("\n[1/3] Loading CSV data...")
    df = load_data()
    total_rows = len(df)
    print(f"✓ Loaded {total_rows:,} rows")
    
    print("\n[2/3] Creating chunks from all rows...")
    chunks = create_chunks(df)
    total_chunks = len(chunks)
    total_batches = (total_chunks + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"✓ Created {total_chunks:,} chunks ({total_batches} batches)")

    start_batch = get_start_batch(total_batches)
    if start_batch > 1:
        print(f"✓ Resuming from batch {start_batch}/{total_batches}")
    
    print("\n[3/3] Uploading chunks to Pinecone...")
    print("-" * 80)
    
    total_uploaded = 0
    start_time = time.time()
    batch_times = []
    
    # Upload in batches
    for batch_num in range(start_batch, total_batches + 1):
        i = (batch_num - 1) * BATCH_SIZE
        batch = chunks[i:i + BATCH_SIZE]
        batch_start = time.time()
        
        # Show progress
        progress_pct = (batch_num / total_batches) * 100
        elapsed = time.time() - start_time
        
        # Estimate time remaining
        if batch_times:
            avg_batch_time = sum(batch_times) / len(batch_times)
            remaining_batches = total_batches - batch_num + 1
            eta_seconds = remaining_batches * avg_batch_time
            eta_str = format_time(eta_seconds)
        else:
            eta_str = "calculating..."
        
        print(f"Batch {batch_num:4d}/{total_batches}: {progress_pct:5.1f}% | "
              f"Elapsed: {format_time(elapsed):>8s} | ETA: {eta_str:>8s}", end="")
        sys.stdout.flush()
        
        # Upload batch
        try:
            result = upsert_chunks_to_pinecone(batch)
            batch_time = time.time() - batch_start
            batch_times.append(batch_time)
            
            if result and result.get('upserted_count'):
                total_uploaded += result['upserted_count']
                save_checkpoint(batch_num, total_batches, total_uploaded)
                print(f" ✓")
            else:
                print(f" ✗ (returned None)")
        except Exception as e:
            print(f" ✗ Error: {str(e)}")
            raise
    
    elapsed = time.time() - start_time
    rate = total_uploaded / elapsed if elapsed > 0 else 0
    
    print("-" * 80)
    print("\n✓ UPLOAD COMPLETE!")
    print(f"  Total chunks uploaded: {total_uploaded:,}")
    print(f"  Time elapsed: {format_time(elapsed)}")
    print(f"  Upload rate: {rate:.1f} chunks/sec")
    print(f"  Average batch time: {(elapsed / total_batches):.2f} seconds")
    print("=" * 80)
    print("\nRAG system is ready to use!")
    print("Try: python main.py \"Your question about the data\"")
    print("=" * 80)
    
except KeyboardInterrupt:
    print("\n\n⚠ Upload interrupted by user")
    print(f"  Progress: {total_uploaded:,} of {total_chunks:,} chunks uploaded")
    sys.exit(0)
except Exception as e:
    print(f"\n✗ ERROR: {type(e).__name__}")
    print(f"  Message: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

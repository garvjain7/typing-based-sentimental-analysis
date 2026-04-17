import uuid
import time
from datetime import datetime, timedelta

class SessionManager:
    def __init__(self, expiry_minutes=5):
        self.sessions = {}
        self.expiry_minutes = expiry_minutes

    def start_session(self, ip_address):
        # Lazy cleanup of expired sessions
        self.cleanup()
        
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "start_time": time.time(),
            "expires_at": time.time() + (self.expiry_minutes * 60),
            "used": False,
            "ip": ip_address
        }
        return session_id

    def validate_session(self, session_id):
        if session_id not in self.sessions:
            return False, "Session not found. Please refresh."
        
        session = self.sessions[session_id]
        
        if time.time() > session["expires_at"]:
            return False, "Session expired (5 min limit)."
        
        if session["used"]:
            return False, "Session already used for prediction."
            
        return True, session

    def mark_used(self, session_id):
        if session_id in self.sessions:
            self.sessions[session_id]["used"] = True

    def cleanup(self):
        now = time.time()
        expired = [sid for sid, s in self.sessions.items() if now > s["expires_at"]]
        for sid in expired:
            del self.sessions[sid]

class TrustScorer:
    @staticmethod
    def calculate_score(features, raw_stats, session_info, session_id="Unknown"):
        """
        Calculates a trust score from 0-100 based on behavioral patterns.
        """
        score = 0
        
        actual_duration = time.time() - session_info["start_time"]
        total_keys = raw_stats.get("total_keys", 0)
        text_length = raw_stats.get("text_length", 1)
        wpm = features.get("wpm", 0)
        avg_delay = features.get("avg_inter_key_delay", 0)

        # 1. Volume Check (Min 100-150 keys) (Max 20 pts)
        if total_keys >= 150: score += 20
        elif total_keys >= 100: score += 10

        # 2. Duration Check (Min 45s) (Max 30 pts)
        if actual_duration >= 45: score += 30
        elif actual_duration >= 30: score += 15

        # 3. Humanity Ratio (Detects Pasting) (Max 25 pts)
        ratio = total_keys / text_length
        if ratio >= 0.9: score += 25
        elif ratio >= 0.7: score += 15

        # 4. Rhythm Validity (Detects Bots) (Max 15 pts)
        if avg_delay >= 50: score += 15
        elif avg_delay >= 25: score += 5

        # 5. Velocity Check (Max 10 pts)
        if wpm <= 130: score += 10
        elif wpm <= 160: score += 5
        
        print(f"\n[SECURITY] Trust Evaluation for Session {session_id}:")
        print(f"  - Keys: {total_keys} (Ratio: {ratio:.2f})")
        print(f"  - Duration: {int(actual_duration)}s")
        print(f"  - Final Score: {score}/100")
        if score < 60:
            print(f"  - STATUS: REJECTED (Below 60 threshold)")
        else:
            print(f"  - STATUS: ACCEPTED")
            
        return score

class RateLimiter:
    def __init__(self, max_requests=10, window_seconds=60):
        self.requests = {} # ip -> [timestamps]
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def is_allowed(self, ip):
        now = time.time()
        if ip not in self.requests:
            self.requests[ip] = [now]
            return True
        
        # Filter timestamps in current window
        self.requests[ip] = [t for t in self.requests[ip] if now - t < self.window_seconds]
        
        if len(self.requests[ip]) >= self.max_requests:
            return False
            
        self.requests[ip].append(now)
        return True

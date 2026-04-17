import numpy as np
import pandas as pd
import random
import datetime

np.random.seed(42)
random.seed(42)

def simulate_session(user_profile, mood, states, mood_state_map):
    """
    Simulates a high-fidelity typing session word-by-word.
    Returns the 10 behavioral features based on the exact logic in metrics.js.
    """
    
    # 1. Choose hidden state based on mood
    state_name = random.choices(
        list(mood_state_map[mood].keys()),
        weights=list(mood_state_map[mood].values())
    )[0]
    s = states[state_name]

    # 2. Session Parameters
    num_words = random.randint(40, 70)
    # Average English word length is ~5.1 chars including space
    # We simulate a "Target WPM" for this user in this state
    target_wpm = user_profile['base_wpm'] * (1 + s['wpm'] * np.random.uniform(0.8, 1.2))
    
    # Scale base hold/delay by state
    m_hold = (1 + s['hold'] * np.random.uniform(0.8, 1.2))
    m_delay = (1 + s['delay'] * np.random.uniform(0.8, 1.2))
    m_error = (1 + s['error'] * np.random.uniform(0.8, 1.2))

    current_time_ms = 0
    start_time = 0
    
    key_down_times = []
    hold_times = []
    word_timestamps = []
    backspace_count = 0
    total_keys = 0
    accumulated_errors = 0
    
    # 3. Simulate Word-by-Word Typing Process
    for w in range(num_words):
        word_len = random.randint(3, 8) # average length variance
        
        # Word typing speed varies slightly (Momentum)
        word_tempo = target_wpm * np.random.uniform(0.9, 1.1)
        # Average time per character (total ms / chars)
        # 1 char = 1/5 of a word (standard)
        char_ms = (60000 / word_tempo) / 5.0
        
        # Split char_ms into hold and delay
        # Hold time is usually 30-40% of the total keystroke cycle
        base_h = user_profile['base_hold'] * m_hold
        base_d = max(10, char_ms - base_h) * m_delay
        
        # Typo Engine
        word_has_error = random.random() < (user_profile['base_error'] * m_error)
        
        chars_in_word = word_len + 1 # +1 for space
        for c in range(chars_in_word):
            # Simulate keydown
            key_down_times.append(current_time_ms)
            total_keys += 1
            
            # Simulate hold time
            h = base_h + np.random.normal(0, 10)
            h = max(50, min(400, h))
            hold_times.append(h)
            
            # Simulate gap to next key
            # Larger gap for spaces (word transitions)
            is_space = (c == chars_in_word - 1)
            gap_noise = np.random.normal(0, 20)
            
            if is_space:
                # Add a "thinking pause" occasionally
                pause_chance = 0.15
                if random.random() < pause_chance:
                    # Simulation a long pause (Stressed/Fatigued more likely)
                    pause_val = user_profile['base_pause'] * (1 + s['pause'] * np.random.uniform(0.8, 1.2))
                    gap = pause_val + np.random.normal(0, 100)
                else:
                    gap = base_d * 2.5 + gap_noise # space gap is wider
            else:
                gap = base_d + gap_noise
            
            # Error Correction Logic
            if word_has_error and c == word_len - 1: # error near end of word
                accumulated_errors += 1
                # User notices and backspaces 1-3 times
                bs_needed = random.randint(1, 3)
                for _ in range(bs_needed):
                    current_time_ms += 150 # backspace reaction time
                    key_down_times.append(current_time_ms)
                    hold_times.append(80) # quick backspaces
                    backspace_count += 1
                    total_keys += 1
                    current_time_ms += 100 # next backspace
                
                # Correction time (typing again)
                current_time_ms += 200 
            
            current_time_ms += max(10, gap)
            
        word_timestamps.append(current_time_ms)

    end_time = current_time_ms
    
    # 4. Feature Calculation (Matching metrics.js exactly)
    
    elapsed_min = (end_time - start_time) / 60000
    wpm = (num_words / elapsed_min) if elapsed_min > 0 else 0
    
    # WPM Variance
    per_word_wpms = []
    for i in range(1, len(word_timestamps)):
        dt = (word_timestamps[i] - word_timestamps[i-1]) / 60000
        if dt > 0: per_word_wpms.append(1 / dt)
    
    wpm_variance = np.var(per_word_wpms) if per_word_wpms else 0
    
    avg_key_hold_time = np.mean(hold_times)
    
    inter_key_delays = []
    for i in range(1, len(key_down_times)):
        gap = key_down_times[i] - key_down_times[i-1]
        if 0 < gap < 5000: inter_key_delays.append(gap)
        
    avg_inter_key_delay = np.mean(inter_key_delays) if inter_key_delays else 0
    
    backspace_rate = backspace_count / total_keys if total_keys > 0 else 0
    error_rate = accumulated_errors / total_keys if total_keys > 0 else 0
    
    pause_threshold = 500
    pause_gaps = [g for g in inter_key_delays if g > pause_threshold]
    avg_pause_time = np.mean(pause_gaps) if pause_gaps else 0
    
    pause_std = np.std(pause_gaps) if pause_gaps else 0
    pause_variability = pause_std / (np.mean(pause_gaps) + 1) if pause_gaps else 0
    
    # Typing Consistency (Per second WPM)
    per_sec_wpms = []
    total_secs = int(end_time / 1000)
    for s_idx in range(total_secs):
        lo = s_idx * 1000
        hi = lo + 1000
        keys_in_sec = len([t for t in key_down_times if lo <= t < hi])
        if keys_in_sec > 0:
            per_sec_wpms.append((keys_in_sec / 5) * 60)
            
    if len(per_sec_wpms) > 1:
        m_sec = np.mean(per_sec_wpms)
        s_sec = np.std(per_sec_wpms)
        typing_consistency_score = max(0, min(1, 1 - (s_sec / m_sec))) if m_sec > 0 else 0
    else:
        typing_consistency_score = 0
        
    burstiness_score = (np.std(inter_key_delays) / (avg_inter_key_delay + 1)) if avg_inter_key_delay > 0 else 0
    
    return {
        "wpm": wpm,
        "wpm_variance": wpm_variance,
        "avg_key_hold_time": avg_key_hold_time,
        "avg_inter_key_delay": avg_inter_key_delay,
        "backspace_rate": backspace_rate,
        "error_rate": error_rate,
        "avg_pause_time": avg_pause_time,
        "pause_variability": min(1, pause_variability),
        "typing_consistency_score": typing_consistency_score,
        "burstiness_score": min(1, burstiness_score)
    }

def generate_full_dataset(num_users=120, num_sessions=(15, 25)):
    # Same base distributions as before
    users = []
    for i in range(num_users):
        skill = np.random.choice(['low', 'medium', 'high'], p=[0.2, 0.6, 0.2])
        if skill == 'low':
            base_wpm = np.random.normal(35, 5)
            base_error = np.random.beta(5, 40)
        elif skill == 'medium':
            base_wpm = np.random.normal(60, 10)
            base_error = np.random.beta(2, 50)
        else:
            base_wpm = np.random.normal(90, 15)
            base_error = np.random.beta(1, 80)

        users.append({
            "user_id": f"user_{i+1:03d}",
            "base_wpm": max(15, base_wpm),
            "base_hold": np.random.uniform(80, 130),
            "base_error": base_error,
            "base_pause": np.random.uniform(300, 800),
        })

    states = {
        "focused": {"wpm": +0.10, "hold": -0.10, "delay": -0.10, "error": -0.15, "pause": -0.20},
        "distracted": {"wpm": -0.05, "hold": 0.0, "delay": +0.15, "error": +0.20, "pause": +0.35},
        "rushed": {"wpm": +0.25, "hold": -0.15, "delay": -0.25, "error": +0.30, "pause": -0.10},
        "fatigued": {"wpm": -0.25, "hold": +0.20, "delay": +0.30, "error": +0.15, "pause": +0.45}
    }

    mood_state_map = {
        "Happy": {"focused": 0.8, "rushed": 0.1, "distracted": 0.1},
        "Neutral": {"focused": 0.3, "distracted": 0.4, "fatigued": 0.3},
        "Stressed": {"rushed": 0.5, "distracted": 0.3, "fatigued": 0.2}
    }

    data = []
    now = datetime.datetime.utcnow()
    
    print(f"Starting word-by-word simulation for {num_users} users...")
    
    for u in users:
        for _ in range(random.randint(*num_sessions)):
            mood = np.random.choice(["Happy", "Neutral", "Stressed"])
            session = simulate_session(u, mood, states, mood_state_map)
            
            # Metadata
            timestamp_offset = datetime.timedelta(minutes=random.randint(0, 43200))
            session["timestamp"] = (now - timestamp_offset).isoformat()
            session["user_id"] = u["user_id"]
            session["mood_label"] = mood
            session["confidence"] = 1.0
            
            data.append(session)
            
    return pd.DataFrame(data)

if __name__ == "__main__":
    df = generate_full_dataset()
    
    # Enforce correct column order
    cols_order = [
        'timestamp', 'user_id', 'wpm', 'wpm_variance', 'avg_key_hold_time',
        'avg_inter_key_delay', 'backspace_rate', 'error_rate', 'avg_pause_time',
        'pause_variability', 'typing_consistency_score', 'burstiness_score',
        'mood_label', 'confidence'
    ]
    df = df[cols_order]
    
    output_path = "backend/data/typing_behavior_dataset.csv"
    df.to_csv(output_path, index=False)
    print(f"High-fidelity dataset generated and ordered: {len(df)} rows.")
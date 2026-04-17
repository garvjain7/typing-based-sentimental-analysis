import numpy as np
import pandas as pd
import random

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

def generate_typing_dataset(num_users=100, num_sessions_per_user=(20, 30)):
    """
    Generates a synthetic typing behavior dataset with hierarchical logic.
    """
    
    # 1. Define User Baselines
    users = []
    for i in range(num_users):
        user_id = f"user_{i+1:03d}"
        
        # Skill level can influence baselines
        skill_level = np.random.choice(['low', 'medium', 'high'], p=[0.2, 0.6, 0.2])
        
        if skill_level == 'low':
            base_wpm = np.random.normal(30, 5)
            base_error_rate = np.random.beta(5, 50) # Low but visible
        elif skill_level == 'medium':
            base_wpm = np.random.normal(60, 10)
            base_error_rate = np.random.beta(2, 50)
        else: # high
            base_wpm = np.random.normal(100, 15)
            base_error_rate = np.random.beta(1, 100)
            
        users.append({
            'user_id': user_id,
            'base_wpm': max(15, base_wpm),
            'base_wpm_variance': np.random.uniform(2, 10),
            'base_hold_time': np.random.uniform(80, 150),
            'base_delay': np.random.uniform(100, 300),
            'base_backspace': np.random.beta(2, 40),
            'base_error_rate': base_error_rate,
            'base_pause_time': np.random.uniform(200, 800),
            'base_pause_var': np.random.uniform(0.2, 0.5),
            'base_consistency': np.random.uniform(0.6, 0.9),
            'base_burstiness': np.random.uniform(0.1, 0.4)
        })
        
    # 2. Mood Factors (Multiplicative scaling)
    # feature = baseline * (1 + mood_factor) + noise
    # Every feature now has a mood signal grounded in typing psychology:
    #   Stressed → more errors, more backspaces, slower, more erratic, less consistent
    #   Happy    → faster, fewer errors, fluid rhythm, fewer corrections
    mood_configs = {
        'Happy': {
            'wpm':              0.12,   # Faster — relaxed and focused
            'wpm_variance':    -0.15,   # More consistent speed across words
            'error_rate':      -0.15,   # Fewer typos
            'hold_time':       -0.08,   # Snappier key presses
            'inter_key_delay': -0.08,   # Less hesitation between keys
            'backspace_rate':  -0.25,   # Far fewer corrections
            'pause_time':      -0.18,   # Shorter thinking pauses
            'pause_variability':-0.15,  # More predictable rhythm
            'consistency':      0.10,   # Higher typing consistency
            'burstiness':      -0.10,   # Steady flow, not bursty
        },
        'Neutral': {
            'wpm': 0.0, 'wpm_variance': 0.0, 'error_rate': 0.0,
            'hold_time': 0.0, 'inter_key_delay': 0.0, 'backspace_rate': 0.0,
            'pause_time': 0.0, 'pause_variability': 0.0,
            'consistency': 0.0, 'burstiness': 0.0,
        },
        'Stressed': {
            'wpm':             -0.15,   # Slower — hesitation and anxiety
            'wpm_variance':     0.35,   # Speed lurches: fast bursts then stops
            'error_rate':       0.30,   # Many more typos under pressure
            'hold_time':        0.15,   # Holding keys longer (tension)
            'inter_key_delay':  0.18,   # Longer gaps between keystrokes
            'backspace_rate':   0.45,   # Frequent corrections
            'pause_time':       0.30,   # Long thinking/recovery pauses
            'pause_variability':0.30,   # Highly irregular pauses
            'consistency':     -0.20,   # Much less consistent rhythm
            'burstiness':       0.35,   # Very erratic typing pattern
        },
    }
    
    # 3. Generate Sessions
    data = []
    for user in users:
        num_sessions = random.randint(*num_sessions_per_user)
        for _ in range(num_sessions):
            mood = np.random.choice(['Happy', 'Neutral', 'Stressed'])
            m_cfg = mood_configs[mood]
            
            # Helper for adding noise and clipping
            def get_val(base, mood_factor, noise_scale, dist='normal', clip=None):
                factor = 1 + (mood_factor * np.random.uniform(0.8, 1.2))
                if dist == 'normal':
                    val = base * factor + np.random.normal(0, noise_scale)
                elif dist == 'lognormal':
                    # Log-normal logic: exp(log(base) + noise)
                    val = np.exp(np.log(base * factor) + np.random.normal(0, noise_scale/base))
                elif dist == 'beta':
                    # Simplified beta-like shift: clip(base * factor + noise, 0, 1)
                    val = base * factor + np.random.normal(0, noise_scale)
                    val = max(0, min(1, val))
                else:
                    val = base * factor + np.random.normal(0, noise_scale)
                
                if clip:
                    val = max(clip[0], min(clip[1], val))
                return val

            # Feature Calculation — every feature now reads its mood factor from m_cfg
            import datetime as dt_module
            row = {
                'timestamp': (dt_module.datetime.utcnow() - dt_module.timedelta(minutes=random.randint(0, 43200))).isoformat(),
                'user_id': user['user_id'],
                'wpm': get_val(user['base_wpm'], m_cfg.get('wpm', 0), 2, clip=(10, 130)),
                'wpm_variance': get_val(user['base_wpm_variance'], m_cfg.get('wpm_variance', 0), 1, clip=(0, 400)),
                'avg_key_hold_time': get_val(user['base_hold_time'], m_cfg.get('hold_time', 0), 10, dist='lognormal', clip=(50, 400)),
                'avg_inter_key_delay': get_val(user['base_delay'], m_cfg.get('inter_key_delay', 0), 20, dist='lognormal', clip=(50, 1000)),
                'backspace_rate': get_val(user['base_backspace'], m_cfg.get('backspace_rate', 0), 0.01, dist='beta', clip=(0, 1)),
                'error_rate': get_val(user['base_error_rate'], m_cfg.get('error_rate', 0), 0.01, dist='beta', clip=(0, 1)),
                'avg_pause_time': get_val(user['base_pause_time'], m_cfg.get('pause_time', 0), 50, dist='lognormal', clip=(50, 2000)),
                'pause_variability': get_val(user['base_pause_var'], m_cfg.get('pause_variability', 0), 0.05, clip=(0, 1)),
                'typing_consistency_score': get_val(user['base_consistency'], m_cfg.get('consistency', 0), 0.05, clip=(0, 1)),
                'burstiness_score': get_val(user['base_burstiness'], m_cfg.get('burstiness', 0), 0.05, clip=(0, 1)),
                'mood_label': mood,
                'confidence': 1.0
            }
            
            # 4. Occasional Random Overrides (10-20%)
            if random.random() < 0.15:
                # Randomize one feature completely
                feat_to_randomize = random.choice([f for f in row.keys() if f not in ['user_id', 'mood_label']])
                if feat_to_randomize in ['error_rate', 'backspace_rate']:
                    row[feat_to_randomize] = np.random.beta(1, 10)
                elif feat_to_randomize == 'wpm':
                    row[feat_to_randomize] = np.random.uniform(10, 130)
                else:
                    row[feat_to_randomize] *= np.random.uniform(0.5, 2.0)
            
            # 5. Rare Outliers (2-5%)
            if random.random() < 0.03:
                row['avg_pause_time'] = np.random.uniform(1500, 2000)
                row['error_rate'] = np.random.uniform(0.4, 0.6)
            
            data.append(row)
            
    return pd.DataFrame(data)

if __name__ == "__main__":
    print("Generating dataset...")
    df = generate_typing_dataset(num_users=120)
    
    # Final CSV export
    output_file = "backend/data/typing_behavior_dataset.csv"
    df.to_csv(output_file, index=False)
    print(f"Successfully generated {len(df)} rows and saved to {output_file}.")
    
    # Quick Summary to console
    print("\nDataset Summary:")
    print(df.groupby('mood_label').size())
    print("\nFeature Averages by Mood:")
    print(df.groupby('mood_label')[['wpm', 'error_rate', 'avg_pause_time']].mean())

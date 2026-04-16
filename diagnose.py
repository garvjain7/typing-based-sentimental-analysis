import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import cross_val_score, StratifiedKFold, train_test_split
from sklearn.dummy import DummyClassifier

df = pd.read_csv('backend/data/typing_behavior_dataset.csv')
features = ['wpm','wpm_variance','avg_key_hold_time','avg_inter_key_delay',
            'backspace_rate','error_rate','avg_pause_time','pause_variability',
            'typing_consistency_score','burstiness_score']
X = df[features]
y = df['mood_label']

payload = joblib.load('backend/model/model.pkl')
model = payload['model']

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

print('=== 5-FOLD CROSS-VALIDATION ===')
scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
print(f'Per-fold: {[round(s,4) for s in scores]}')
print(f'Mean: {scores.mean():.4f}  Std: {scores.std():.4f}')

print()
print('=== RANDOM BASELINE ===')
dummy = DummyClassifier(strategy='most_frequent')
d_scores = cross_val_score(dummy, X, y, cv=cv, scoring='accuracy')
print(f'Dummy mean: {d_scores.mean():.4f}')

print()
print('=== OVERFITTING CHECK ===')
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
model.fit(X_tr, y_tr)
train_acc = model.score(X_tr, y_tr)
test_acc  = model.score(X_te, y_te)
print(f'Train accuracy: {train_acc:.4f}')
print(f'Test  accuracy: {test_acc:.4f}')
print(f'Gap (overfit?): {train_acc - test_acc:.4f}')

print()
print('=== ROOT CAUSE: Within-user noise vs Between-mood signal ===')
user_wpm_std = df.groupby('user_id')['wpm'].std().mean()
between_mood_wpm = df.groupby('mood_label')['wpm'].mean()
mood_wpm_signal = between_mood_wpm.max() - between_mood_wpm.min()
ratio = user_wpm_std / mood_wpm_signal
print(f'Avg within-user WPM std:   {user_wpm_std:.2f}')
print(f'Between-mood WPM range:    {mood_wpm_signal:.2f}')
print(f'Noise-to-signal ratio:     {ratio:.1f}x  (>1 means noise drowns signal)')

print()
user_pt_std = df.groupby('user_id')['avg_pause_time'].std().mean()
between_pt  = df.groupby('mood_label')['avg_pause_time'].mean()
pt_signal   = between_pt.max() - between_pt.min()
ratio2 = user_pt_std / pt_signal
print(f'Avg within-user pause_time std: {user_pt_std:.2f}')
print(f'Between-mood pause_time range:  {pt_signal:.2f}')
print(f'Noise-to-signal ratio:          {ratio2:.1f}x')

print()
print('=== MOOD FACTOR MAGNITUDES (from generate_dataset.py) ===')
print('Stressed burstiness factor: 0.25  (25% bump)')
print('Stressed error_rate factor: 0.15  (15% bump)')
print('Stressed pause_time factor: 0.20  (20% bump)')
print('Happy    wpm factor:        0.08  ( 8% bump)')
print('Happy    error_rate factor:-0.05  ( 5% reduction)')
print()
print('Actual mean % differences measured in dataset:')
means = df.groupby('mood_label')[features].mean()
neutral = means.loc['Neutral']
for mood in ['Happy', 'Stressed']:
    diffs = ((means.loc[mood] - neutral) / neutral * 100)
    top = diffs.abs().nlargest(5)
    print(f'\n  {mood} top-5 differences from Neutral:')
    for feat, val in top.items():
        print(f'    {feat:<35} {val:+.2f}%')

print()
print('=== KEY FINDING: features NOT affected by mood ===')
unaffected = ['wpm_variance', 'avg_inter_key_delay', 'backspace_rate',
              'pause_variability', 'typing_consistency_score']
print('These features have 0.0 mood factor in generate_dataset.py:')
for f in unaffected:
    print(f'  {f}')
print(f'That is {len(unaffected)}/10 features = pure noise for the classifier')

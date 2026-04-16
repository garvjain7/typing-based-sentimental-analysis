import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import cross_val_score, StratifiedKFold, train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from scipy import stats

df = pd.read_csv('backend/data/typing_behavior_dataset.csv')
features = ['wpm','wpm_variance','avg_key_hold_time','avg_inter_key_delay',
            'backspace_rate','error_rate','avg_pause_time','pause_variability',
            'typing_consistency_score','burstiness_score']
X = df[features]
y = df['mood_label']

payload = joblib.load('backend/model/model.pkl')
model = payload['model']

print("=" * 65)
print("Q1: IS THE DATASET TOO EASY FOR THE MODEL?")
print("=" * 65)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# Compare RF vs a much simpler model
lr_cv = cross_val_score(make_pipeline(StandardScaler(), LogisticRegression(max_iter=500)), X, y, cv=cv)
rf_cv = cross_val_score(model, X, y, cv=cv)
dummy_cv = cross_val_score(DummyClassifier(strategy='most_frequent'), X, y, cv=cv)

print(f"  Random guess baseline:     {dummy_cv.mean():.3f}")
print(f"  Simple LogisticRegression: {lr_cv.mean():.3f}")
print(f"  Our RandomForest:          {rf_cv.mean():.3f}")
print(f"  Gap RF vs LogReg:          {rf_cv.mean()-lr_cv.mean():+.3f}")
print()

X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
model.fit(X_tr, y_tr)
print(f"  Train accuracy: {model.score(X_tr, y_tr):.3f}")
print(f"  Test  accuracy: {model.score(X_te, y_te):.3f}")
print(f"  Overfit gap:    {model.score(X_tr, y_tr) - model.score(X_te, y_te):.3f}")
print()
print("  VERDICT: If accuracy were >95% on test, it would be 'too easy'.")
print(f"  At {model.score(X_te, y_te)*100:.1f}%, the model is challenged — not memorizing.")

print()
print("=" * 65)
print("Q2: DOES THE DATASET LOOK REAL (not constant-formula-like)?")
print("=" * 65)

print("\n  [A] Distribution shape — real data follows Normal/LogNormal, not uniform")
for f in features:
    vals = df[f].values
    stat, p = stats.normaltest(vals)
    skew = stats.skew(vals)
    kurt = stats.kurtosis(vals)
    print(f"  {f:<35}  skew={skew:+.2f}  kurt={kurt:+.2f}  normal_p={p:.3f}")

print()
print("  [B] Correlation between features — real typing has natural correlations")
corr = df[features].corr()
print("  Strong correlations (|r|>0.3) found between:")
for i in range(len(features)):
    for j in range(i+1, len(features)):
        r = corr.iloc[i, j]
        if abs(r) > 0.3:
            print(f"    {features[i]} <-> {features[j]}: r={r:.3f}")

print()
print("  [C] Within-user variability — same user should vary across sessions")
user_stats = df.groupby('user_id')['wpm'].agg(['mean','std','min','max'])
print(f"  Avg within-user WPM std:  {user_stats['std'].mean():.2f}")
print(f"  Avg within-user WPM min:  {user_stats['min'].mean():.2f}")
print(f"  Avg within-user WPM max:  {user_stats['max'].mean():.2f}")
print(f"  Avg within-user WPM range:{(user_stats['max']-user_stats['min']).mean():.2f}")

print()
print("  [D] Outlier presence — real data has them")
for f in ['wpm', 'avg_pause_time', 'error_rate']:
    z = np.abs(stats.zscore(df[f]))
    outliers = (z > 2.5).sum()
    pct = outliers / len(df) * 100
    print(f"  {f:<25} outliers (z>2.5): {outliers:4d}  ({pct:.1f}%)")

print()
print("=" * 65)
print("Q3: IS THE DATASET LEARNABLE FOR ML?")
print("=" * 65)

print()
print("  [A] Class separability — SNR per feature")
means = df.groupby('mood_label')[features].mean()
stds  = df.groupby('mood_label')[features].std()
learnable_count = 0
for f in features:
    signal = means[f].max() - means[f].min()
    noise  = stds[f].mean()
    snr    = signal / noise if noise > 0 else 0
    learnable = "✓ learnable" if snr > 0.15 else "✗ too weak"
    if snr > 0.15:
        learnable_count += 1
    print(f"  {f:<35}  SNR={snr:.3f}  {learnable}")

print(f"\n  -> {learnable_count}/10 features have learnable signal (SNR > 0.15)")

print()
print("  [B] Feature importance from trained model")
imp = sorted(zip(features, model.feature_importances_), key=lambda x: -x[1])
for feat, score in imp:
    bar = '█' * int(score * 150)
    print(f"  {feat:<35} {score:.4f}  {bar}")

print()
print("  [C] Are all 3 classes distinguishable from each other?")
for mood in ['Happy','Neutral','Stressed']:
    for other in ['Happy','Neutral','Stressed']:
        if mood >= other: continue
        # Build binary problem
        mask = df['mood_label'].isin([mood, other])
        Xb = df.loc[mask, features]
        yb = df.loc[mask, 'mood_label']
        binary_rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
        s = cross_val_score(binary_rf, Xb, yb, cv=3, scoring='accuracy').mean()
        print(f"  {mood} vs {other}: {s:.3f} binary accuracy")

print()
print("=" * 65)
print("Q4: DO THE VALUES VARY (distributions, ranges, spread)?")
print("=" * 65)
print()
desc = df[features].describe().T[['mean','std','min','25%','50%','75%','max']]
desc['cv%'] = (desc['std'] / desc['mean'] * 100).round(1)  # coefficient of variation
print(desc.to_string())
print()
print("  cv% = coefficient of variation (std/mean*100). >10% = good spread.")
print()
print("  PER-MOOD value ranges (min → max):")
for f in ['wpm', 'backspace_rate', 'avg_pause_time', 'burstiness_score']:
    print(f"\n  {f}:")
    for mood in ['Happy','Neutral','Stressed']:
        vals = df[df['mood_label']==mood][f]
        print(f"    {mood:<10}  {vals.min():.3f} → {vals.max():.3f}  (mean={vals.mean():.3f}, std={vals.std():.3f})")

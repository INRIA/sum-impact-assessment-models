# gaia_pymcdm.py — GAIA avec rayons de critères (PyMCDM seulement)
import numpy as np
import numpy.linalg as la
import matplotlib.pyplot as plt
from pymcdm.methods.partial import PROMETHEE_I
from pymcdm.methods import PROMETHEE_II
from sklearn.decomposition import PCA

# --------- Données (exemple : tes voitures) ---------
# RMO: BUSINESS ACTIVITIES (measures)
alts = ["Tourism B","Luxury 1","Tourism A","Luxury 2"]
# RMO: CRITERIA / GOALS scores (from KPI groups) - observed KPI values ? 
X = np.array([
    [23000, 85, 7.0, 4],
    [38000, 90, 8.5, 4],
    [26000, 75, 8.0, 3],
    [35000, 85, 9.0, 5],
], float)

# -1 = coût (minimiser), +1 = bénéfice (maximiser)
# RMO: ????? GOAL TYPES
types = np.array([-1, +1, -1, +1], int)

# Poids et fonction de préférence (adapte à ta config)
# RMO: GOAL WEIGHTS
W = np.array([0.25, 0.25, 0.25, 0.25], float)
# RMO: GOAL PREFERENCE FUNCTION ???
pref = 'vshape'               # 'usual','ushape','vshape','level','vshape_2'
# RMO: GOAL PREFERENCE PARAMETERS ???
p = np.array([15000., 15., 2., 2.], float)
q = None                      # si tu veux une zone d'indifférence: pref='vshape_2' et mets q

# --------- Flots PROMETHEE I & II (pour vérifier) ---------
phi_plus, phi_minus = PROMETHEE_I(pref, p=p, q=q)(X, W, types)
phi = PROMETHEE_II(pref, p=p, q=q)(X, W, types)
print("Flows ([-1,1])")
for a, pp, pm, pn in zip(alts, phi_plus, phi_minus, phi):
    print(f"{a:10s}  Phi={pn:.4f}  Phi+={pp:.4f}  Phi-={pm:.4f}")

# --------- GAIA: unicritères -> SVD ---------
m, n = X.shape
PhiJ = np.zeros((m, n))  # unicriterion net flows φ_j = φ+_j - φ-_j

# calcule φ_j en mettant un poids 1 sur le critère j, 0 sur les autres
for j in range(n):
    wj = np.zeros(n); wj[j] = 1.0
    pp_j, pm_j = PROMETHEE_I(pref, p=p, q=q)(X, wj, types)
    PhiJ[:, j] = pp_j - pm_j

#GAIA MANUELLEMENT
# pondérer par W et centrer les colonnes (pratique GAIA)
PhiJw = PhiJ * W
C = PhiJw - PhiJw.mean(axis=0, keepdims=True)

# SVD => coordonnées alternatives (scores) & rayons critères (loadings)
U, S, VT = la.svd(C, full_matrices=False)
scores = U[:, :2] * S[:2]   # alt coords (axes U,V)
loadings = VT[:2, :].T      # criteria rays

# qualité de projection (comme "Qualité %")
quality = (S[:2]**2).sum() / (S**2).sum() * 100.0
print(f"GAIA quality (U,V): {quality:.1f}%")

# axe de décision π (projection des poids dans le plan U–V)
w_norm = W / W.sum()
pi_vec = (loadings * w_norm[:, None]).sum(axis=0)  
# mise à l'échelle pour l'affichage
scale = 1.15 * max(1e-9 + np.linalg.norm(scores, axis=1))
pi_draw = pi_vec / (np.linalg.norm(pi_vec) + 1e-12) * scale

# --------- Tracé ---------
plt.figure(figsize=(7,6))
# alternatives
plt.scatter(scores[:,0], scores[:,1])
print("Alternative scores:")
for i, name in enumerate(alts):
    print(f"{name}: {scores[i,0]}, {scores[i,1]}")
    plt.annotate(name, (scores[i,0], scores[i,1]), xytext=(5,5), textcoords="offset points")

# rayons des critères
print("Loadings (criteria rays):")
for j, lab in enumerate(["Price","Power","Consumption","Habitability"]):
    print(loadings[j, :])
    plt.arrow(0, 0, loadings[j,0]*scale, loadings[j,1]*scale,
              head_width=0.02*scale, length_includes_head=True)
    plt.annotate(lab, (loadings[j,0]*scale, loadings[j,1]*scale),
                 xytext=(3,3), textcoords="offset points")

# axe π
plt.arrow(0, 0, pi_draw[0], pi_draw[1],
          head_width=0.03*scale, length_includes_head=True, linestyle='--')
plt.annotate('π (decision axis)', (pi_draw[0], pi_draw[1]),
             xytext=(3,3), textcoords="offset points")

# axes & titres
plt.axhline(0, linewidth=0.5); plt.axvline(0, linewidth=0.5)
plt.xlabel("U"); plt.ylabel("V")
plt.title(f"GAIA-style biplot — quality {quality:.1f}%")
plt.tight_layout()
plt.savefig("gaia_pymcdm_manual.png", dpi=150)
# plt.show()

# --------- GAIA avec PCA (vérification) ---------
# X_norm = (X - X.mean(axis=0)) / X.std(axis=0)
pca = PCA(n_components=2)
scores_pca = pca.fit_transform(PhiJw)
loadings_pca = pca.components_.T

fig, ax = plt.subplots(figsize=(7, 6))
ax.scatter(scores_pca[:, 0], scores_pca[:, 1])
print(f"PCA singular values: {pca.singular_values_}")
for i, name in enumerate(alts):
    print(f"PCA scores for {name}: {scores_pca[i, 0]}, {scores_pca[i, 1]}")
    ax.annotate(name, (scores_pca[i, 0], scores_pca[i, 1]), xytext=(5, 5), textcoords="offset points")

print(f"PCA explained variance ratios: {pca.explained_variance_ratio_}")
for j, lab in enumerate(["Price","Power","Consumption","Habitability"]):
    print(loadings_pca[j, :])
    ax.arrow(0, 0, loadings_pca[j, 0]*scale, loadings_pca[j, 1]*scale,
             head_width=0.02*scale, length_includes_head=True)
    ax.annotate(lab, (loadings_pca[j, 0]*scale, loadings_pca[j, 1]*scale),
                xytext=(3, 3), textcoords="offset points")
    
# axe π
pi_vec_pca = (loadings_pca * w_norm[:, None]).sum(axis=0)
pi_draw_pca = pi_vec_pca / (np.linalg.norm(pi_vec_pca) + 1e-12) * scale
ax.arrow(0, 0, pi_draw_pca[0], pi_draw_pca[1],
         head_width=0.03*scale, length_includes_head=True, linestyle='--')
ax.annotate('π (decision axis)', (pi_draw_pca[0], pi_draw_pca[1]),
            xytext=(3, 3), textcoords="offset points")

ax.axhline(0, linewidth=0.5); ax.axvline(0, linewidth=0.5)
ax.set_xlabel("PC1"); ax.set_ylabel("PC2")
ax.set_title("GAIA-style biplot with PCA")
plt.tight_layout()
plt.savefig("gaia_pymcdm_pca.png", dpi=150)
# plt.show()
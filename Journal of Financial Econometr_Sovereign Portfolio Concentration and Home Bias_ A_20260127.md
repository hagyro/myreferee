# Referee Report

**Paper**: Sovereign Portfolio Concentration and Home Bias: A Gradient Boosting Analysis  
**Journal**: Journal of Financial Econometrics  
**Recommendation**: Major Revision

---

## 1. Summary

This paper applies machine learning methods—including TabPFN, CatBoost, and NGBoost—to predict sovereign home bias among European banks using EBA Transparency Exercise data (2016–2024). The main findings are that ML models achieve high out-of-sample R² (0.92–0.95), substantially outperforming linear benchmarks, with SHAP analysis revealing that portfolio concentration (HHI) and lagged home bias dominate predictive importance, while bank fundamentals contribute modestly. A methodological contrast emerges: whereas ML explains 94% of cross-sectional variance, two-way panel fixed effects explain only 6% of within-bank variation, suggesting home bias is a persistent bank characteristic rather than a dynamic response variable.

---

## 2. Contribution & Journal Fit

### Main Contribution

The paper offers three contributions: (1) demonstrating that ML methods can predict home bias with high accuracy, (2) constructing a comprehensive panel from 4.5 million EBA records, and (3) contrasting ML prediction with panel econometrics to reveal that cross-sectional variation dominates within-bank dynamics. The SHAP-based decomposition provides interpretable insights for supervisory applications.

### Journal Fit Assessment

The Journal of Financial Econometrics publishes methodologically rigorous work at the intersection of financial economics and econometric/statistical methods. This paper fits the journal's scope in its application of modern ML techniques to a policy-relevant financial question. However, several concerns affect fit:

1. **Methodological novelty is limited**: The paper applies existing ML methods (CatBoost, TabPFN) rather than developing new econometric techniques. JoFE typically expects methodological contributions beyond pure application.

2. **Econometric analysis is underdeveloped**: The panel fixed effects analysis (6% R² for within-variation) is presented as a contrast to ML but receives minimal methodological treatment. This comparison could be substantially deepened.

3. **The paper reads more like applied finance than financial econometrics**: The emphasis on supervisory applications and SHAP importance rankings, while valuable, does not engage deeply with the econometric literature on panel prediction, model comparison, or out-of-sample inference.

**Verdict**: The paper is within scope but at the boundary. Strengthening the econometric content—particularly the ML vs. panel comparison and inference framework—would improve fit considerably.

---

## 3. Major Concerns

### Major Concern 1: Incomplete Manuscript

**Issue**: The paper appears truncated. The text ends mid-sentence in the Methodology section ("When features are correlated (as with HHI and Top3 Share), attribution among correlated feat—"). The Results section is referenced but not present. Section 5 (Robustness Checks) and Section 6 (Conclusion) are mentioned but missing entirely.

**Why it matters**: It is impossible to evaluate the paper's empirical claims, robustness, or conclusions without the complete manuscript. The reported R² values (0.92–0.95) appear only in the Introduction and cannot be verified.

**Suggested fix**: Submit the complete manuscript including Results, Robustness Checks, and Conclusion sections with all tables and figures referenced in the text.

---

### Major Concern 2: Endogeneity of Portfolio Concentration Features

**Issue**: The dominant predictor (HHI, accounting for "54%" of model importance per the Introduction) is mechanically related to the target variable. A bank with high home bias will, by construction, tend to have high portfolio concentration if its domestic holding is large. The HHI across country exposures and the share of domestic exposure are not independent quantities.

**Why it matters**: The high predictive accuracy may reflect near-tautological relationships rather than economically meaningful prediction. Predicting home bias using portfolio concentration is analogous to predicting obesity using waist circumference—statistically valid but limited in economic insight.

**Suggested fix**: 
- Report model performance *excluding* HHI, Top3 Share, and lagged home bias to isolate the predictive content of bank fundamentals alone. The Introduction mentions R² of 0.64–0.70 for fundamentals-only models—this should be the primary specification.
- Clearly distinguish between "prediction" (forecasting a quantity) and "explanation" (identifying causal mechanisms). The mechanically-related features aid the former but not the latter.
- Consider instrumental variable approaches or Granger-style tests to establish whether fundamentals *predict future changes* in home bias.

---

### Major Concern 3: Lagged Dependent Variable Dominates

**Issue**: Lagged home bias accounts for 17% of SHAP importance, and including it raises R² from 0.64–0.70 to 0.90–0.92. This persistence is expected given the finding that panel fixed effects explain most cross-sectional variation.

**Why it matters**: High persistence means the ML model is largely predicting that home bias tomorrow equals home bias today. This is economically trivial. The policy-relevant question is: what predicts *changes* in home bias or *deviations* from a bank's historical average?

**Suggested fix**:
- Estimate models predicting the *first difference* (ΔHomeBias) or *demeaned* home bias. The Introduction mentions first differences as a robustness check—this should be a primary specification.
- Report how much predictive accuracy derives from fundamentals when predicting changes rather than levels.
- Discuss the half-life of home bias shocks implied by the persistence estimates.

---

### Major Concern 4: Inadequate Treatment of Panel Structure

**Issue**: The temporal train-test split (pre-2022 vs. 2022–2024) is appropriate, but the cross-validation scheme described ("each bank appears entirely within a single fold") may not adequately address the panel structure. The paper does not discuss:
- Serial correlation in prediction errors within banks
- Cluster-robust inference for the Diebold-Mariano test
- Whether the R² metric is computed on pooled test observations or averaged within periods

**Why it matters**: Standard errors and hypothesis tests assuming independent observations will be severely understated with panel data. The reported bootstrap confidence intervals and DM p-values may be unreliable.

**Suggested fix**:
- Report period-by-period R² in addition to pooled R².
- Use block bootstrap at the bank level for confidence intervals.
- Compute the Diebold-Mariano test with Newey-West or cluster-robust standard errors.
- Discuss how prediction accuracy varies across the test period (is the model stable, or does accuracy degrade?).

---

### Major Concern 5: Causality vs. Prediction Conflation

**Issue**: The paper oscillates between prediction claims ("can ML models accurately predict") and causal/explanatory claims ("reveal the mechanisms driving this portfolio allocation," "identifying key drivers"). SHAP values measure predictive importance, not causal effects.

**Why it matters**: Policy conclusions require causal understanding. Stating that "portfolio concentration accounts for 54% of importance" suggests concentration *causes* home bias, but this is not established.

**Suggested fix**:
- Clearly separate predictive and causal objectives throughout the paper.
- Acknowledge that SHAP importance does not identify causal mechanisms.
- If causal claims are intended, discuss identification strategies (e.g., regulatory changes as natural experiments, difference-in-differences around EBA policy shifts).

---

### Major Concern 6: Missing Model Comparison Details

**Issue**: The paper claims ML "significantly outperforms" linear benchmarks but provides no details on:
- Hyperparameter values selected for each model
- Feature engineering/preprocessing steps
- Whether all models use identical feature sets
- Computational details (training time, convergence)

**Why it matters**: Reproducibility requires complete specification. The reader cannot assess whether the comparison is fair (e.g., whether Ridge regression received equivalent tuning effort).

**Suggested fix**:
- Include a table reporting final hyperparameters for all models.
- Provide a replication package with code and (where permissible) data.
- Ensure Ridge/Lasso models use the same features as ML models.

---

## 4. Minor Concerns

1. **Sample attrition unclear**: The paper notes 1,972 raw observations reduced to 1,066 complete cases, a 46% reduction. Which variables drive missingness? Is selection bias a concern?

2. **Peripheral country indicator**: The binary peripheral indicator (GIIPS) is crude. Consider continuous measures of sovereign risk or allow for heterogeneous effects by country.

3. **TabPFN operational constraints**: The paper notes TabPFN accommodates up to 1,024 training observations, but the training set has 528 observations—well within limits. Clarify why this constraint is mentioned.

4. **SHAP correlation caveat incomplete**: The Methodology section is cut off while discussing SHAP limitations with correlated features. This discussion is essential given the HHI-Top3 Share correlation.

5. **No mention of alternative home bias definitions**: Literature uses multiple definitions (e.g., normalized by benchmark portfolio weights, deviation from market portfolio). Robustness to alternative definitions should be discussed.

6. **Time-varying feature importance not analyzed**: Do the drivers of home bias change over the sample period (e.g., pre/post COVID, before/after ECB QE)? SHAP analysis could be conducted by subperiod.

7. **Bank fixed effects in ML**: The paper does not discuss whether bank identifiers are included as features in ML models. If so, this would mechanically capture time-invariant heterogeneity and conflate model types.

8. **No discussion of model uncertainty for TabPFN**: TabPFN provides Bayesian predictions—are posterior predictive intervals reported? How do they compare to NGBoost uncertainty estimates?

9. **Regulatory implications overstated**: Claims about supervisory applications require validation against actual supervisory outcomes (e.g., do high-predicted-home-bias banks exhibit worse performance during stress?).

10. **Literature review gaps**: No mention of Altavilla et al. (2017) on QE and bank portfolios, or Acharya and Steffen (2015) on the "greatest carry trade ever."

---

## 5. Robustness Checklist

The following tests are needed (status unknown due to missing Results/Robustness sections):

- [ ] Fundamentals-only model (excluding HHI, Top3, lagged DV)
- [ ] First-difference specification (predicting ΔHomeBias)
- [ ] Demeaned specification (within-bank variation only)
- [ ] Alternative home bias definitions (benchmark-adjusted)
- [ ] Period-by-period R² rather than pooled
- [ ] Subsample analysis by bank size quartiles
- [ ] Subsample analysis by country (core vs. periphery separately)
- [ ] Placebo tests (randomized target variable)
- [ ] Feature ablation study (sequential removal of top features)
- [ ] Sensitivity to train-test split date (2020 vs. 2021 vs. 2022 cutoff)
- [ ] Comparison with static panel models (pooled OLS, random effects)
- [ ] Model calibration plots for NGBoost uncertainty
- [ ] SHAP dependence plots for top features
- [ ] Interaction effects between HHI and bank characteristics

---

## 6. Section-by-Section Analysis

### Introduction

**Strengths**:
- Clear motivation linking sovereign home bias to systemic risk (doom loop).
- Well-articulated research questions.
- Upfront statement of main findings.

**Weaknesses**:
- Claims about R² values cannot be verified without Results section.
- The "54% importance for HHI" finding is presented without acknowledging the mechanical relationship concern.
- The ML-vs-panel comparison (94% vs. 6%) is intriguing but underexplained in the introduction.

**Suggestions**:
- Temper claims about "revealing mechanisms"—reframe as predictive importance.
- Add a paragraph discussing the paper's limitations upfront.

---

### Literature Review (Section 2.1)

**Strengths**:
- Comprehensive coverage of sovereign-bank nexus literature (Brunnermeier et al., Farhi & Tirole, De Marco & Macchiavelli).
- Clear organization around three mechanisms (moral suasion, regulatory incentives, information asymmetries).
- Identification of the gap: no ML applications to home bias.

**Weaknesses**:
- Missing key references: Acharya & Steffen (2015) "The Greatest Carry Trade Ever," Altavilla et al. (2017) on ECB QE effects.
- No discussion of the econometric literature on panel prediction or ML in econometrics (Mullainathan & Spiess, 2017; Athey & Imbens, 2019).
- The claim of "zero papers" applying ML to home bias requires a more systematic literature search methodology.

**Suggestions**:
- Add a paragraph on the econometrics of prediction vs. inference.
- Discuss how this paper relates to the ML-in-economics methodological literature.

---

### Institutional Context (Section 2.2)

**Strengths**:
- Detailed description of EBA Transparency Exercise mechanics.
- Clear explanation of CRR sovereign exposure treatment (zero risk weights, no large exposure limits).
- Policy relevance well established.

**Weaknesses**:
- No discussion of data quality issues (reporting errors, restatements).
- Time series of regulatory changes (e.g., IFRS 9 adoption in 2018) not discussed.

**Suggestions**:
- Add a paragraph on potential data quality concerns.
- Discuss whether IFRS 9 adoption affects measurement consistency.

---

### Data (Section 3)

**Strengths**:
- Clear description of panel construction from 4.5M raw records.
- Standard home bias definition consistent with literature.
- Complete variable descriptions with three-category organization.

**Weaknesses**:
- Summary statistics table referenced but not shown.
- Missing discussion of measurement error in bank characteristics.
- No correlation matrix showing feature relationships (essential given SHAP interpretation concerns).

**Suggestions**:
- Include correlation matrix for key features.
- Discuss potential measurement error in CET1 ratios, ROA.
- Report distribution of observations across countries.

---

### Methodology (Section 4)

**Strengths**:
- Appropriate temporal holdout design.
- Comprehensive model suite (foundation model, gradient boosting, probabilistic, linear).
- SHAP methodology clearly explained.

**Weaknesses**:
- Section is incomplete (cuts off mid-sentence).
- No discussion of hyperparameter tuning protocol details.
- The claim that "blocking prevents information leakage" is too strong—within-bank serial correlation remains.
- No discussion of computational requirements.

**Suggestions**:
- Complete the SHAP limitations discussion.
- Add hyperparameter grid specifications.
- Discuss what happens if blocking by bank is relaxed.

---

### Results (Missing)

Cannot evaluate.

---

### Robustness Checks (Missing)

Cannot evaluate.

---

### Conclusion (Missing)

Cannot evaluate.

---

## 7. Positioning

### Comparison to Recent JoFE Publications

Reviewing recent JoFE publications reveals the following expectations:

1. **Methodological depth**: Papers like Gu, Kelly & Xiu (2020, RFS—related methodology) or Bianchi, Büchner & Tamoni (2021, JoFE) combine ML applications with careful econometric analysis of why ML works (bias-variance tradeoffs, which nonlinearities matter).

2. **Economic content**: JoFE papers typically use empirical findings to inform economic theory, not just prediction accuracy.

3. **Inference framework**: Even prediction-focused papers discuss uncertainty quantification, model confidence sets, and the limitations of point forecasts.

This paper's strengths relative to JoFE standards:
- Policy relevance (doom loop) is high.
- Data construction effort (EBA panel) is substantial.
- The ML-vs-panel contrast could be a distinctive contribution.

This paper's weaknesses relative to JoFE standards:
- Methodological contribution is limited (application of existing methods).
- Economic interpretation is shallow (SHAP importance ≠ economic mechanisms).
- Inference framework is underdeveloped (panel structure, uncertainty).

**Positioning recommendation**: Reframe the paper around the ML-vs-panel methodological question ("What does it mean when ML explains 94% of cross-sectional variance but FE explain only 6% of within-variance?"). This is a novel finding with broader methodological implications. The current framing as a pure prediction exercise is less suitable for JoFE.

---

## 8. Editor Note

This paper addresses a policy-relevant question—predicting sovereign home bias among European banks—using modern machine learning methods applied to a carefully constructed supervisory dataset. The core empirical finding that ML achieves high cross-sectional prediction accuracy while panel fixed effects explain minimal within-bank variation is potentially interesting.

However, I cannot recommend acceptance in its current form for three reasons. First, the manuscript is incomplete, with missing Results, Robustness, and Conclusion sections. Second, major methodological concerns—particularly the mechanical relationship between portfolio concentration features and the target variable, and the dominance of lagged dependent variables—undermine the substantive interpretation of the high R² values. Third, the paper's positioning as a prediction exercise does not fully engage with JoFE's methodological standards; deeper econometric analysis of the ML-vs-panel comparison would strengthen fit substantially.

**Recommendation**: Major Revision. The authors should (1) submit the complete manuscript, (2) address the endogeneity and persistence concerns through fundamentals-only and first-difference specifications, (3) develop the ML-vs-panel comparison as a methodological contribution, and (4) separate predictive accuracy claims from causal/mechanistic claims throughout. With these revisions, the paper could make a meaningful contribution to JoFE.

---

## 9. To-Do List

**Priority 1: Essential (manuscript incomplete or claims unverifiable)**

1. Submit complete manuscript including Results, Robustness Checks, and Conclusion sections.
2. Include all referenced tables and figures.

**Priority 2: Critical (major concerns affecting validity)**

3. Report model performance excluding HHI, Top3 Share, and lagged home bias (fundamentals-only specification).
4. Estimate first-difference models predicting ΔHomeBias as a primary specification.
5. Address mechanical relationship between portfolio concentration and home bias explicitly.
6. Use cluster-robust inference (block bootstrap, clustered standard errors) for all statistical tests.
7. Separate predictive importance (SHAP) from causal claims throughout the paper.

**Priority 3: Important (affects interpretation and fit)**

8. Report period-by-period R² and analyze prediction stability over time.
9. Include correlation matrix for features and discuss implications for SHAP interpretation.
10. Add hyperparameter specifications and replication code availability statement.
11. Reframe the ML-vs-panel comparison as a methodological contribution.
12. Discuss whether bank identifiers are included as ML features.

**Priority 4: Recommended (improves quality)**

13. Add missing literature references (Acharya & Steffen 2015, Altavilla et al. 2017).
14. Discuss sample attrition (1,972 → 1,066) and potential selection bias.
15. Report NGBoost and TabPFN uncertainty estimates and calibration.
16. Conduct subperiod SHAP analysis (pre/post COVID, QE periods).
17. Consider continuous sovereign risk measures instead of binary peripheral indicator.

**Priority 5: Optional (strengthens contribution)**

18. Test alternative home bias definitions (benchmark-adjusted).
19. Conduct feature ablation study.
20. Discuss regulatory implications with more specificity about supervisory applications.

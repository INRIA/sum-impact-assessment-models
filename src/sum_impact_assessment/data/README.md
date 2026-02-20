The information in the mcda_goals_ba_configuration.json file is the final result of expert surveys done by VEDECOM. 
The methodology for the calculations is described bellow. 
Authors : "Axel Le Dreau", VEDECOM 

Note:
We start from stakeholder interviews conducted across several Living Labs. During
these interviews, participants assessed the Business Activities (BA) implemented in
their own Living Lab. BA are groups of push and pull measures. For each BA, they
provided a qualitative score for each policy goal, using a 1–5 scale. Each score is
therefore linked to a respondent (actor), a Living Lab, a stakeholder category (for
example PTO, Regulatory, NSM provider), a BA, and a goal. A key feature of the
dataset is that not all Living Labs implemented the same BA. As a result, actors only
score the BAs that exist in their site, which creates an unbalanced and incomplete
evaluation grid.
For decision support, we do not simply average the interview scores. A raw mean (or
median) per BA and goal would mix several effects that are not the BA performance.
First, Living Labs differ in local context, and implementation conditions can influence
how impacts are perceived, so some sites may systematically rate higher or lower.
Second, stakeholder categories often have different perspectives, which can lead to
systematic differences in ratings. Third, individuals use the 1–5 scale differently:
some respondents are generally stricter, others more generous. Finally,
representation is uneven: some categories or sites are more represented in
interviews and would dominate a simple average. In addition, some BAs are rated by
only a few actors. In those cases, a mean can be unstable. Because of these issues,
we aim to produce a scoring table that is fair across stakeholder groups, comparable
across sites, and robust when data are sparse.
We use a Bayesian ordinal hierarchical model (also called a multilevel cumulative
logit model) to transform the interview ratings into a robust BA-Goal scoring matrix.
“Ordinal” means the method is designed for ordered scores such as 1–5, where
higher is better but the exact distance between levels is not assumed to be perfectly
linear. “-Hierarchical (multilevel) means it explicitly accounts for the structure of the
data: respondents belong to a Living Lab (site) and to a stakeholder category, and
each respondent may have a consistent rating style (more strict or more generous).
The model estimates a typical score for each BA and goal while separating BArelated differences from systematic differences linked to sites, stakeholder
categories, and individual rating habits. Because it is Bayesian, it naturally produces
both a central estimate and an uncertainty range for each BA-oal score, which helps
communicate where evidence is strong or limited.
Process :
The first methodological choice is to treat the 1–5 interview score as an ordered
judgement rather than a precise measurement. A score of 4 means “better than 3”,
but we do not assume that the numerical distance between 2 and 3 is exactly the
same as between 4 and 5. We therefore treat scores as ordered categories. This
avoids over-interpreting the exact numeric gap between rating levels and better
reflects the qualitative nature of interview-based scoring.
We then estimate a typical BA score for each goal while controlling for systematic
differences in the data. Conceptually, for each goal we separate four components.
The BA effect captures whether a given BA tends to receive higher or lower scores
on that goal; this is the performance signal we are interested in for comparison
across BA. The site effect captures whether a Living Lab context tends to shift ratings
up or down for that goal, reflecting differences in local conditions and implementation
environments. The stakeholder category effect captures whether certain actor groups
tend to rate differently on that goal due to perspective or institutional role. The actor
effect captures individual rating style, meaning that some respondents are
consistently strict or consistently generous across all their ratings. Estimating these
components together allows us to distinguish “this BA is rated higher” from “this site
rates higher” or “this actor rates higher”, which improves comparability across BAs
despite the incomplete coverage of the evaluation grid.
To ensure fairness between stakeholder categories, we apply a balancing rule during
model estimation. Because categories are not equally represented, we prevent any
single group from dominating the estimated BA performance simply due to sample
size. In practice, each individual rating is given an estimation weight so that each
stakeholder category has equal total influence, each actor has equal influence within
their category, and actors who rated more BAs do not automatically count more than
actors who rated fewer BAs. A diagnostic file is produced to verify that this balancing
behaves as intended.
The model does not directly output a single number per BA and goal. Instead, for
each BA–goal pair it produces a probability distribution across possible score levels.
This means the result is not only a point estimate but also expresses how likely each
rating level is, given the data and the adjustments described above. To build the
input matrix required by PROMETHEE, we convert this distribution into a score using
an expected value approach: we multiply each score level by its probability and sum
the results. The resulting value remains on the familiar 1–5 scale, but it is grounded
in the full distribution rather than in a single observed rating.
When producing the final BA×goal matrix, we deliberately compute a score that is not
tied to a specific site, stakeholder category, or individual respondent. This is done by
predicting BA performance as if the site context were average, the stakeholder
category were average, and the actor rating style were average, while retaining only
the BA-specific effect for each goal. The purpose is to obtain one comparable score
per BA and goal that can be used consistently in PROMETHEE, even though the
underlying interview data were collected in different sites with different respondent
mixes.
Finally, we report uncertainty. Some BA–goal scores are supported by more interview
ratings than others. For each BA and goal we therefore compute a central estimate
and a 95% uncertainty range. This is important for interpretation: if two BAs are close
in score but their uncertainty ranges overlap substantially, the evidence for a
difference is weaker and rankings should be interpreted with caution.
The process produces two main outputs. The first is a BA-goal performance matrix
containing the typical score for each BA on each goal; this is the direct input for
PROMETHEE. The second is the same information in a long format with the
associated uncertainty bounds, which supports transparency and allows users to
identify where results are robust versus uncertain. The resulting scores represent
stakeholder-perceived performance, adjusted to be fair and comparable across sites
and stakeholder groups. They do not directly measure real-world KPI changes, which
can be assessed separately using KPI-based methods.
Ref
Ohnishi, Y., & Sugaya, S. (2022). Applying Bayesian hierarchical probit model to
interview grade evaluation. arXiv preprint arXiv:2003.11591.
Johnson, V. E. (1994). On Bayesian analysis of multi-rater ordinal data: An
application to automated essay grading. Institute of Statistics and Decision Sciences,
Duke University, Discussion Paper 94-03
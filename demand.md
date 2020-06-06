---
title: Demand Modeling Cookbook
author: '@ajfriend'
date: 2020-03-29
---


We can mix-and-match a few different ideas for improving our demand model. This doc tries to suggest a few potential approaches.

What we choose would depend on what we think the impact would be.

# Base model

**Problem**: You need a simple model to forecast demand going to each restaurant as a function of additive BAF.

**Solution**: Model orders over a time window (say, 5 minutes) as a Poisson random variable
with mean

$$
\mu = S \exp\left(\beta^0 + \beta^1 p \right)
$$

where

- $S$ is the number of sessions currently in the city
- $p$ is the additive BAF price currently active at this time
- $\beta^0$ describes the base order rate of the restaurant (its popularity)
- $\beta^1$ describes how price dampens demand

**Model training**:

To estimate $\beta^0$ and $\beta^1$ for **a single restaurant**, we can compute a maximum likelihood fit by solving the optimization problem:

$$
\begin{array}{ll}
\text{maximize} & \sum_{i=1}^N y_i \log \mu_i - \mu_i \\
\text{subject to} & \mu_i = S_i \exp(\beta^0 + \beta^1 p_i)
\end{array}
$$

where observation $i$ consists of:

- the number of active sessions $S_i$ at that time
- the additive BAF $p_i$
- $y_i$ observed orders placed during the time

**Notes**:

- can also train over multiple restaurants and have them each have a distinct $\beta^1$ parameter (if there is enough data), or have them share a single, common $\beta^1$
- we can train different models for different times of day or times of week, although this can start to cause data sparsity issues
- this model **does not** account for realtime radii changes or effects due to BAF/radii locking in the app

**Historical issues with the model**:

- data sparsity in some hours causes poor estimation of $\beta^1$
- if there is very little BAF in a market due to seasonal trends or over-supply, it is hard to estimate $\beta^1$
- it is hard to estimate demand coming from new restaurants, which might have no historical data

# Naive radii model

**Problem**: Restaurant delivery radii change in real time to dampen demand.

**Solution**: Modify the base model to account for radii changes.

Assume that each restaurant has a "typical" default radius, and that we can observe the delivery radius at any time as $r \in [0, 1]$, the fraction of the max radius.

Assume the dampening fraction due to radius $r$ is given by $r^\alpha$. The Poisson mean becomes

$$
\begin{aligned}
\mu &= S r^\alpha \exp\left(\beta^0 + \beta^1 p\right)\\
&= \exp \left[ \log(S) + \alpha \log(r) + \beta^0 + \beta^1 p \right]
\end{aligned}
$$

**Notes**

- still the usual Poisson regression
- don't need to think about using $r$ vs. $r^2$ as a feature; the exponent gets absorbed in $\alpha$
- might consider a single city-wide $\alpha$ along with $\beta^1$

**Potential issues**

- doesn't account for BAF or radii locking
- assumes a radially symmetric demand for each restaurant (no knowledge of hex-specific densities)


# BAF locking

**Problem**: A newly selected BAF value will not influence all users immediately, as some are still locked in to old values.

**Solution**: Model upcoming orders in the next minute as a sum of Poisson variables, each representing the state of the world (sessions, BAF value) over previous minutes.

For a single restaurant, let

- $t \in \lbrace -1, -2, \ldots, -N\rbrace$ be a minute in the past
- $S_t$ be the number of active sessions in the city at minute $t$
- $p_t$ the additive BAF value at $t$
- $\tau_t$ be the relative influence of minute $t$ on the upcoming minute
    - $\tau \in \mathbf{R}_+^N$ and $\sum_t \tau_t = 1$
    - assume distribution $\tau$ is the same for all restaurants and all times

The Poisson mean for a single minute is then

$$
\begin{aligned}
\mu &= \sum_{t=-1}^{-N} \tau_t S_t \exp\left(\beta^0 + \beta^1 p_t\right)\\
&= \exp \left(\beta^0\right) \sum_t \tau_t S_t \exp\left(\beta^1 p_t\right)
\end{aligned}
$$

**Model training**

$$
\begin{array}{ll}
\text{maximize} & \sum_{i=1}^N y_i \log \mu_i - \mu_i \\
\text{subject to} & \mu_i = \exp \left(\beta^0\right) \sum_t \tau_t S_{i,t}\exp\left(\beta^1 p_{i,t}\right)\\
& \sum_t \tau_t = 1\\
& \tau \geq 0\\
\end{array}
$$

- this problem is no longer convex, but still very tractable
    - convex in $\beta^0$ and $\tau$, but not in $\beta^1$
    - however, we can do alternating minimization, and just do a 1D search for $\beta^1$

**Notes**

- can start with an initial reasonable guess for $\tau$
- can set $S_t = 0$ for minutes the restaurant is closed (relevant in the minutes right after the restaurant opens)
- do we need minute granularity?
    - BAF and radii change independently.
    - does any 5 minute bin represent it accurately?


# Hourly regularization

**Problem**: We get poor $\beta^1$ estimates for low-volume times of day.

**Solution**: Add regularization to penalize differences in parameters between adjacent hours of day. Hours with few data points will then be incentivized to adopt similar parameters to their neighbors.

We'll consider a model for a **single restaurant**:

- suppose we have $\beta^0$ and $\beta^1$ parameters for each hour of day
    - that is, $\beta^0, \beta^1 \in \mathbf{R}^{24}$

observation $i$ consists of:

- $S_i$ sessions in the city at that time
- placed orders $y_i$
- local hour of day $h_i$
- additive BAF $p_i$
- hour-specific $\beta$ parameters $\beta^0_{h_i}$, $\beta^1_{h_i}$

The order rate is modeled as a Poisson random variable with mean

$$
\mu_i = S_i \exp\left(\beta^0_{h_i} + \beta^1_{h_i} p_i\right)
$$

The maximum likelihood parameter estimation problem is then

$$
\begin{array}{ll}
\text{maximize} & \sum_i y_i \log \mu_i - \mu_i \\
\text{subject to} & \mu_i = S_i \exp\left(\beta^0_{h_i} + \beta^1_{h_i} p_i\right)\\
\end{array}
$$

- however, there is no coupling between hours of the day in the above problem
- adding a penalty for neighboring hours to differ in parameters adds coupling and can help produce a more reasonable estimate for hours with low data
- let $C \in \mathbf{R}^{24 \times 24}$ be a circular difference matrix

The regularized problem would then be

$$
\begin{array}{ll}
\text{maximize} & -\rho_0 \|C\beta^0\|_1 - \rho_1\|C \beta^1 \|_1 + \frac{1}{N}\sum_{i=1}^N y_i \log \mu_i - \mu_i \\
\text{subject to} & \mu_i = S_i \exp\left(\beta^0_{h_i} + \beta^1_{h_i} p_i\right)\\
\end{array}
$$

- $\rho_0, \rho_1$ give the strength of the regularization
- different norms can be used for the regularization above

**Notes**

- this model could be combined with the BAF locking recipe, or the radii recipe


# Very few surge events

**Problem**: The market is over-supplied, so there are very few surge events, or the market has not previously had BAF. Thus, the price response $\beta^1$  is hard to estimate.

**Solution**: Use a Bayesian approach to incorporate prior knowledge around reasonable values for $\beta^1$.

- fix price response to a previously-estimated constant $\beta^1_*$:
- 
$$
\begin{array}{ll}
\text{maximize} & \sum_{i=1}^N y_i \log \mu_i - \mu_i \\
\text{subject to} & \mu_i = S_i \exp(\beta^0 + \beta^1 p_i)\\
& \beta^1 = \beta^1_*
\end{array}
$$

- prescribe a prior distribution on $\beta^1$:

$$
\begin{array}{ll}
\text{maximize} & -\rho\left(\beta^1 - \beta^1_*\right)^2 + \frac{1}{N}\sum_{i=1}^N y_i \log \mu_i - \mu_i \\
\text{subject to} & \mu_i = S_i \exp(\beta^0 + \beta^1 p_i)\\
\end{array}
$$

# Hex-specific radii model

**Problem**: Instead of using city-wide sessions, we want to only use sessions within the current delivery radius for a restaurant, and take into account the hex-specific distribution of session counts.

**Solution**: Model demand at a restaurant as a sum of Poisson variables, one for each hexagon within the delivery radius.

- let $H$ be the set of hexagons currently with in the restaurant delivery radius
- $S_h$ be the count of active sessions in hexagon $h$
- $d_h$ be some measure of distance between the restaurant and hexagon $h$
- $\beta^2$ describes the order dampening due to distance from the restaurant

$$
\begin{aligned}
\mu &= \sum_{h \in H} S_h \exp\left(\beta^0 + \beta^1 p + \beta^2 d_h \right)\\
&= \exp \left(\beta^0 + \beta^1p \right) \sum_{h \in H} S_h \exp\left( \beta^2 d_h \right)\\
\end{aligned}
$$



# Locking and hex-specific model

- let $\mu$ be the rate of orders being placed at a restaurant over the upcoming **1 minute**
- we'll model this as a sum of poisson random variables, one for each minute over the previous **30 minutes**

$$
\begin{aligned}
\mu &= \sum_t \tau_t S_{t,h} \exp\left(\beta^0 + \beta^1 p_t + \beta^2 d_h \right)\\
&= \exp(\beta^0 + \beta^2 d_h) \sum_t \tau_t S_{t,h} \exp\left(\beta^1 p_t\right)
\end{aligned}
$$


observation $i$ consists of:

- restaurant $r_i$
- delivery hexagon $h_i$
- $y_i$ orders in minute $t=0$
- set of previous 30 minutes $T = \lbrace -1, -2, \ldots, -30 \rbrace$
- $S_{t,h_i}$ sessions ($0$ if outside current delivery radius)
- $p_{t,r_i}$ additive surge price of $r_i$ at time $t$
- $d_{r_i, h}$ integer hex distance between $r_i$ and hex $h$

model parameters:

- time discount factors (due to BAF and radii locking) $\tau \in \mathbf{R}^{30}$
- $\beta^0_{r_i}$ base order rate
- $\beta^1$ response to BAF price
- $\beta^2$ response to distance

$$
\begin{array}{ll}
\text{maximize} & \sum_i y_i \log \mu_i - \mu_i \\
\text{subject to} & \mu_i = \exp(\beta^0_{r_i} + \beta^2 d_{r_i,h_i}) \sum_{t \in T}   \tau_t S_{t,h_i} \exp\left(\beta^1 p_{t, r_i}  \right)\\
& \sum_t \tau_t = 1\\
& \tau \geq 0\\
& \beta^1, \beta^2 \leq 0
\end{array}
$$


## model training

- we can train by holding subsets of parameters constant
    - alternating minimization

Hold all variables constant except:

- $\beta^1$
    - not quite convex, but is just 1D (can search for optimal)

$$
\begin{array}{ll}
\text{maximize}_{\beta^1} & \sum_i y_i \log \mu_i - \mu_i \\
\text{subject to} & \mu_i = \sum_{t \in T}   c_{i,t} \exp\left(\beta^1 p_t  \right)\\
\end{array}
$$

- $\tau$
    - convex

$$
\begin{array}{ll}
\text{maximize}_{\tau} & \sum_i y_i \log\left(c_i^T \tau \right) - c_i^T \tau \\
\text{subject to}
& \mathbf{1}^T \tau = 1\\
& \tau \geq 0
\end{array}
$$

- $\beta^0$ and $\beta^2$
    - convex; just regular Poisson regression

$$
\begin{array}{ll}
\text{maximize}_{\beta^0, \beta^2} & \sum_i y_i \log \mu_i - \mu_i \\
\text{subject to} & \mu_i = c_i \exp(\beta^0_{r_i} + \beta^2 d_{r_i,h_i})\\
\end{array}
$$

# Evaluation

- which of these modifications are worth doing?


# BAF locking (5-minutes)

- assume no radii reduction

For a single restaurant, let

- $t \in \lbrace 0, -1, \ldots, -N\rbrace$ index the upcoming 5 minute bin and the $N$ previous 5-minute bins
- $S_t$ be the number of active sessions in the city at time $t$
- $p_t$ the **average** additive BAF value within bin $t$
- $\tau_t$ be the relative influence of time $t$ on the upcoming bin
    - $\tau \in \mathbf{R}_+^{N+1}$ and $\sum_t \tau_t = 1$
    - assume distribution $\tau$ is the same for all restaurants and all times
- $y$ be the number of orders placed in bin $t=0$

The Poisson for the orders in bin $t=0$ is then

$$
\begin{aligned}
\mu &= \sum_{t=0}^{-N} \tau_t S_t \exp\left(\beta^0 + \beta^1 p_t\right)\\
&= \exp \left(\beta^0\right) \sum_t \tau_t S_t \exp\left(\beta^1 p_t\right)
\end{aligned}
$$

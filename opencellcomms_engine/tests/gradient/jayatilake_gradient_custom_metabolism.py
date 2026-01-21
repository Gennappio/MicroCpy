import math

# === Lactate Production Rate ===
def lactate_production(mu_o2, A0, CG, KG, glycoATP):
    """
    R_Lp: Lactate production rate

    Parameters:
    - mu_o2: oxygen utilization rate
    - A0: reference ATP yield factor
    - CG: glucose concentration (mM)
    - KG: Michaelis constant for glucose (mM)
    - glycoATP: 1 if glycolytic ATP production is active, else 0

    Returns:
    - Lactate production rate (float)
    """
    return (2 * mu_o2 / 6) * (A0 / 2) * (CG / (KG + CG)) * glycoATP

# === Lactate Consumption Rate ===
def lactate_consumption(mu_o2, CO2, KO2, CL, KL, mitoATP):
    """
    R_Lc: Lactate consumption rate

    Parameters:
    - mu_o2: oxygen utilization rate
    - CO2: oxygen concentration (mM)
    - KO2: Michaelis constant for oxygen (mM)
    - CL: lactate concentration (mM)
    - KL: Michaelis constant for lactate (mM)
    - mitoATP: 1 if mitochondrial ATP production is active, else 0

    Returns:
    - Lactate consumption rate (float)
    """
    return (2 * mu_o2 / 6) * (CO2 / (KO2 + CO2)) * (CL / (KL + CL)) * mitoATP

# === Oxygen Consumption Rate ===
def oxygen_consumption(mu_o2, CO2, KO2, mitoATP, glycoATP, K=0.5):
    """
    R_O2: Oxygen consumption rate

    Parameters:
    - mu_o2: oxygen utilization rate
    - CO2: oxygen concentration (mM)
    - KO2: Michaelis constant for oxygen (mM)
    - mitoATP: 1 if mitochondrial ATP production is active, else 0
    - glycoATP: 1 if glycolytic ATP production is active, else 0
    - K: weighting factor for glycoATP contribution (default 0.5)

    Returns:
    - Oxygen consumption rate (float)
    """
    return mu_o2 * (CO2 / (KO2 + CO2)) * (mitoATP + K * glycoATP)

# === ATP Production Rate ===
def atp_production(mu_o2, A0, CO2, KO2, CG, KG, mitoATP, glycoATP):
    """
    R_ATP: Total ATP production rate

    Parameters:
    - A0: reference ATP factor
    - mu_o2: oxygen utilization rate
    - CO2: oxygen concentration
    - KO2: Michaelis constant for O2
    - CG: glucose concentration
    - KG: Michaelis constant for glucose
    - mitoATP: 1 if mitochondrial ATP active
    - glycoATP: 1 if glycolytic ATP active

    Returns:
    - ATP production rate (float)
    """
    term1 = A0 * (mu_o2 / 6) * (CO2 / (KO2 + CO2)) * (CG / (KG + CG)) * mitoATP
    term2 = A0 * (mu_o2 / 6) * (CG / (KG + CG)) * glycoATP
    return term1 + term2

# === Glucose Consumption Rate ===
def glucose_consumption(mu_o2, A0, CO2, KO2, CG, KG, mitoATP, glycoATP):
    """
    R_G: Glucose consumption rate

    Parameters:
    - mu_o2: oxygen utilization rate
    - A0: ATP factor
    - CO2: oxygen concentration
    - KO2: Michaelis constant for O2
    - CG: glucose concentration
    - KG: Michaelis constant for glucose
    - mitoATP: 1 if mitochondrial ATP active
    - glycoATP: 1 if glycolytic ATP active

    Returns:
    - Glucose consumption rate (float)
    """
    term1 = (mu_o2 / 6) * (CO2 / (KO2 + CO2)) * (CG / (KG + CG)) * mitoATP
    term2 = (mu_o2 * A0 / 6 / 2) * (CG / (KG + CG)) * glycoATP
    return term1 + term2

# === Proton (H+) Production Rate ===
def proton_production(beta, A0, mu_o2, CG, KG, glycoATP):
    """
    R_H+: Proton production rate (acidification)

    Parameters:
    - beta: proportionality constant for proton release
    - A0: ATP scaling constant
    - mu_o2: oxygen utilization rate
    - CG: glucose concentration
    - KG: Michaelis constant for glucose
    - glycoATP: 1 if glycolytic ATP is active, else 0

    Returns:
    - H+ production rate (float)
    """
    return beta * A0 * (mu_o2 / 6) * (CG / (KG + CG)) * glycoATP

# === Extracellular pH Calculation ===
def extracellular_pH(H_concentration):
    """
    Calculate extracellular pH from proton concentration.

    Parameters:
    - H_concentration: [H+] in mol/L

    Returns:
    - pH value (float)
    """
    return -math.log10(H_concentration)

# === Growth Factor Consumption ===
def growth_factor_consumption(gamma_sc, Cs):
    """
    R_S: Growth factor/inhibitor consumption rate

    Parameters:
    - gamma_sc: consumption rate constant
    - Cs: concentration of substance S

    Returns:
    - Consumption rate (float)
    """
    return gamma_sc * Cs

# === Growth Factor Production ===
def growth_factor_production(gamma_sp):
    """
    R_S: Growth factor production rate

    Parameters:
    - gamma_sp: production rate constant

    Returns:
    - Production rate (float)
    """
    return gamma_sp

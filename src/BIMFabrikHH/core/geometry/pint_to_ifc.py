from pint import UnitRegistry

ureg = UnitRegistry()

Dim = ureg.get_dimensionality

L  = Dim('[length]')
A  = Dim('[length]')**2
V  = Dim('[length]')**3
M  = Dim('[mass]')
T  = Dim('[time]')
I  = Dim('[current]')
Θ  = Dim('[temperature]')
N  = Dim('[substance]')
J  = Dim('[luminosity]')

rad_dim = ureg.radian.dimensionality
sr_dim  = ureg.steradian.dimensionality

P = M / (L * T**2)

pint_to_ifc = {
    L:  'IfcLengthMeasure',
    A:  'IfcAreaMeasure',
    V:  'IfcVolumeMeasure',
    M:  'IfcMassMeasure',
    T:  'IfcTimeMeasure',
    I:  'IfcElectricCurrentMeasure',
    Θ:  'IfcThermodynamicTemperatureMeasure',
    N:  'IfcAmountOfSubstanceMeasure',
    J:  'IfcLuminousIntensityMeasure',
    rad_dim: 'IfcPlaneAngleMeasure',
    sr_dim:  'IfcSolidAngleMeasure',
    P:  'IfcPressureMeasure',
    ureg.dimensionless: 'IfcReal',
}

if __name__ == "__main__":
    assert pint_to_ifc[ureg.meter.dimensionality] == 'IfcLengthMeasure'

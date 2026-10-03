"""bodysim: cuerpo humano paramétrico para simular fisiología y enfermedad.

Capas (de abajo arriba): individuo (variables independientes) -> anatomía
enlazada a UBERON -> escalado anatómico -> [fisiología, genética, enfermedad].
"""

from bodysim.adiposity import FatDistribution
from bodysim.anatomy import Anatomy, Kind, Model3D, Structure, load_anatomy
from bodysim.anthropometry import BodyComposition, body_composition
from bodysim.person import Person, Sex
from bodysim.scaling import MassReport, Modifier, OrganMass, organ_masses, reference_person

__all__ = [
    "Anatomy",
    "BodyComposition",
    "FatDistribution",
    "Kind",
    "MassReport",
    "Model3D",
    "Modifier",
    "OrganMass",
    "Person",
    "Sex",
    "Structure",
    "body_composition",
    "load_anatomy",
    "organ_masses",
    "reference_person",
]

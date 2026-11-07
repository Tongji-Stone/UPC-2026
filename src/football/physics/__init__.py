"""足球飞行正向模型，单位为 SI。"""
from .model import (PhysicsConfig, FlightResult, simulate, forces, reynolds_table,
                    reynolds_spin_table, linthorne_patel_coefficients, coefficients,
                    state_derivative, rotational_torque, config_record, validate_config,
                    kiratidis_leinweber_coefficients, zero_spin_drag, MODEL_ID)

__all__ = ["PhysicsConfig", "FlightResult", "simulate", "forces", "reynolds_table", "reynolds_spin_table", "linthorne_patel_coefficients", "coefficients", "state_derivative", "rotational_torque", "config_record", "validate_config", "kiratidis_leinweber_coefficients", "zero_spin_drag", "MODEL_ID"]

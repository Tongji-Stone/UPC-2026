static inline mjtNum mji_pow2(const mjtNum val) {
  return val*val;
}

static inline mjtNum mji_ellipsoid_max_moment(const mjtNum size[3], const int dir) {
  const mjtNum d0 = size[dir], d1 = size[(dir+1) % 3], d2 = size[(dir+2) % 3];
  return 8.0/15.0 * mjPI * d0 * mji_pow4(mju_max(d1, d2));
}


// lift and drag forces due to motion in the fluid
void mj_viscousForces(
  const mjtNum local_vels[6], const mjtNum fluid_density,
  const mjtNum fluid_viscosity, const mjtNum size[3],
  const mjtNum magnus_lift_coef, const mjtNum kutta_lift_coef,
  const mjtNum blunt_drag_coef, const mjtNum slender_drag_coef,
  const mjtNum ang_drag_coef, mjtNum local_force[6])
{
  const mjtNum lin_vel[3] = {local_vels[3], local_vels[4], local_vels[5]};
  const mjtNum ang_vel[3] = {local_vels[0], local_vels[1], local_vels[2]};
  const mjtNum volume = 4.0/3.0 * mjPI * size[0] * size[1] * size[2];
  const mjtNum d_max = mju_max(mju_max(size[0], size[1]), size[2]);
  const mjtNum d_min = mju_min(mju_min(size[0], size[1]), size[2]);
  const mjtNum d_mid = size[0] + size[1] + size[2] - d_max - d_min;
  const mjtNum A_max = mjPI * d_max * d_mid;

  mjtNum magnus_force[3];
  mji_cross(magnus_force, ang_vel, lin_vel);
  magnus_force[0] *= magnus_lift_coef * fluid_density * volume;
  magnus_force[1] *= magnus_lift_coef * fluid_density * volume;
  magnus_force[2] *= magnus_lift_coef * fluid_density * volume;

  // the dot product between velocity and the normal to the cross-section that
  // defines the body's projection along velocity is proj_num/sqrt(proj_denom)
  const mjtNum proj_denom = mji_pow4(size[1] * size[2]) * mji_pow2(lin_vel[0]) +
                            mji_pow4(size[2] * size[0]) * mji_pow2(lin_vel[1]) +
                            mji_pow4(size[0] * size[1]) * mji_pow2(lin_vel[2]);
  const mjtNum proj_num = mji_pow2(size[1] * size[2] * lin_vel[0]) +
                          mji_pow2(size[2] * size[0] * lin_vel[1]) +
                          mji_pow2(size[0] * size[1] * lin_vel[2]);

  // projected surface in the direction of the velocity
  const mjtNum A_proj = mjPI * mju_sqrt(proj_denom/mju_max(mjMINVAL, proj_num));

  // not-unit normal to ellipsoid's projected area in the direction of velocity
  const mjtNum norm[3] = {
    mji_pow2(size[1] * size[2]) * lin_vel[0],
    mji_pow2(size[2] * size[0]) * lin_vel[1],
    mji_pow2(size[0] * size[1]) * lin_vel[2]
  };

  // cosine between velocity and normal to the surface
  // divided by proj_denom instead of sqrt(proj_denom) to account for skipped normalization in norm
  const mjtNum cos_alpha = proj_num / mju_max(
    mjMINVAL, mju_norm3(lin_vel) * proj_denom);
  mjtNum kutta_circ[3];
  mji_cross(kutta_circ, norm, lin_vel);
  kutta_circ[0] *= kutta_lift_coef * fluid_density * cos_alpha * A_proj;
  kutta_circ[1] *= kutta_lift_coef * fluid_density * cos_alpha * A_proj;
  kutta_circ[2] *= kutta_lift_coef * fluid_density * cos_alpha * A_proj;
  mjtNum kutta_force[3];
  mji_cross(kutta_force, kutta_circ, lin_vel);

  // viscous force and torque in Stokes flow, analytical for spherical bodies
  const mjtNum eq_sphere_D = 2.0/3.0 * (size[0] + size[1] + size[2]);
  const mjtNum lin_visc_force_coef = 3.0 * mjPI * eq_sphere_D;
  const mjtNum lin_visc_torq_coef = mjPI * eq_sphere_D*eq_sphere_D*eq_sphere_D;

  // moments of inertia used to compute angular quadratic drag
  const mjtNum I_max = 8.0/15.0 * mjPI * d_mid * mji_pow4(d_max);
  const mjtNum II[3] = {
    mji_ellipsoid_max_moment(size, 0),
    mji_ellipsoid_max_moment(size, 1),
    mji_ellipsoid_max_moment(size, 2)
  };
  const mjtNum mom_visc[3] = {
    ang_vel[0] * (ang_drag_coef*II[0] + slender_drag_coef*(I_max - II[0])),
    ang_vel[1] * (ang_drag_coef*II[1] + slender_drag_coef*(I_max - II[1])),
    ang_vel[2] * (ang_drag_coef*II[2] + slender_drag_coef*(I_max - II[2]))
  };

  const mjtNum drag_lin_coef =  // linear plus quadratic
                               fluid_viscosity*lin_visc_force_coef + fluid_density*mju_norm3(lin_vel)*(
    A_proj*blunt_drag_coef + slender_drag_coef*(A_max - A_proj));
  const mjtNum drag_ang_coef =  // linear plus quadratic
                               fluid_viscosity * lin_visc_torq_coef +
                               fluid_density * mju_norm3(mom_visc);

  local_force[0] -= drag_ang_coef * ang_vel[0];
  local_force[1] -= drag_ang_coef * ang_vel[1];
  local_force[2] -= drag_ang_coef * ang_vel[2];
  local_force[3] += magnus_force[0] + kutta_force[0] - drag_lin_coef*lin_vel[0];
  local_force[4] += magnus_force[1] + kutta_force[1] - drag_lin_coef*lin_vel[1];
  local_force[5] += magnus_force[2] + kutta_force[2] - drag_lin_coef*lin_vel[2];
}


// read the geom_fluid_coefs array into its constituent parts
void readFluidGeomInteraction(const mjtNum* geom_fluid_coefs,
                              mjtNum* geom_fluid_coef,
                              mjtNum* blunt_drag_coef,
                              mjtNum* slender_drag_coef,
                              mjtNum* ang_drag_coef,
                              mjtNum* kutta_lift_coef,
                              mjtNum* magnus_lift_coef,
                              mjtNum virtual_mass[3],
                              mjtNum virtual_inertia[3]) {
  int i = 0;
  geom_fluid_coef[0]   = geom_fluid_coefs[i++];
  blunt_drag_coef[0]   = geom_fluid_coefs[i++];

"""Signal inversion"""

__author__ = 'Cyril Grima'

from scipy import integrate
import numpy as np
from numpy import cos, exp, log, log10, pi, sqrt
from importlib import import_module
from subradar import Fresnel, Signal, utils
import matplotlib.pyplot as plt


nan = float('nan')


def srf2power_norminc(model, approx, gain=lambda th:1, th_max=nan,
                      db=True, kind='isotropic gaussian', **kwargs):
    """Power components over circular footprint at normal incident
    from surface properties

    PARAMETERS
    ==========
    gain: function
        function of the observation angle (radian) and return
        a linear amplitude

    th_max: float
        Maximum observation angle corresponding to the edge of the footprint

    **kwargs: to be passed to the model (do not include theta)

    EXAMPLE
    =======
    In[1]: sr.invert.srf2power_norminc('iem','Small_S', th_max=0.008,
           wf=13.78e9, ep2=1.5, sh=1.5e-3, cl=100e-3)
    Out[1]:
    {'pc': -23.172003557542929,
    'pn': -36.370086693995717,
    'ratio': 13.198083136452789}
    """

    m = import_module('subradar.' + model)
    Scattering = getattr(m, approx)

    # Coherent Signal
    a = Scattering(th=0, **kwargs)
    pc = a.R['nn']**2 * exp( -(2*a.wk*a.sh)**2 )

    # Incoherent Signal
    # Note: nRCS(th=0) approximation all over the footprint.
    # That allows to get nRCS out of the integral for faster computation
    nRCS = lambda th: Scattering(th=th, **kwargs).nRCS(kind=kind)['hh']
    integrand = lambda th: 2* gain(th)**2 * np.arctan(th)/(th**2+1)
    pn = integrate.quad(integrand, 0, th_max)[0] *nRCS(0)

    # Output
    ratio = pc/pn
    if db:
        pc, pn, ratio = 10*log10(pc), 10*log10(pn), 10*log10(ratio)
    return {'pc':pc, 'pn':pn, 'ratio':ratio}


def power2srf_norminc(model, approx, pc, pn, gain=lambda th:1, wf=nan,
              th_max=nan, db=True, kind='isotropic gaussian',
              ep_range=[1.4,2.5], cl_logrange=[-1, 2], n=50, verbose=False):
    """Surface properties from Power components [in dB]
    """
    pc = 10**(pc/10.)
    s = Signal(wf=wf, bw=nan, th=th_max)

    ep = np.linspace(ep_range[0], ep_range[1], n)
    r = utils.R(1, ep, 1, 1, s.th)
    cl = 10**np.linspace(cl_logrange[0], cl_logrange[1], n)

    sh = sqrt(log(r**2/pc)) / (2*s.wk*cos(s.th))
    sh[np.isnan(sh)] = 0

    cl_out = np.nan * cl

    jn = n
    for i, val in enumerate(ep):
        if verbose is True:
            print('\n')
        if sh[i] != 0: #if no solution for sh, do not compute
            for j in reversed(range(0, jn, 1)):
                tmp = srf2power_norminc(model, approx, gain=gain, th_max=th_max, wf=wf,
                      ep2=ep[i], sh=sh[i], cl=cl[j])['pn']
                if verbose is True:
                    print('[%04d - %04d] ep = %05.2f, sh= %09.6f, cl = %08.3f, pn = %05.1f'
                          % (i, j, ep[i], sh[i], cl[j], tmp))
                if (tmp < pn) and ~np.isinf(tmp):
                    jn = j+1
                    if jn > n:
                        jn = n
                    cl_out[i] = cl[j]
                    break

    return {'ep':ep, 'sh':sh, 'cl':cl_out}

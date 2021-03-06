from utils.run_functions import remove_negative, brightness_error
from processing.getPixels import get_pixels
from processing.getGratvityCentre import find_gravity_centre
from copy import deepcopy
from utils.structures import *


class CentroidSimpleWrapper:
    
    def __init__(self, image, init_x, init_y, A, B, noise_dim, alpha,local_noise, \
                 delta, pix_lim, pix_prop, max_iter, min_iter, snr_lim, fine_iter, is_point ):

        self.image = image
        self.init_x = init_x
        self.init_y = init_y
        self.A = A
        self.B = B
        self.noise_dim = noise_dim
        self.alpha = alpha
        self.local_noise = local_noise
        self.delta = delta
        self.pix_lim = pix_lim
        self.pix_prop = pix_prop
        self.max_iter = max_iter
        self.min_iter = min_iter
        self.snr_lim = snr_lim
        self.fine_iter = fine_iter
        self.is_point = is_point

    def multiset_diff(self, s, t):

        s = np.sort(s)
        t = np.sort(t)
        n = []
        i = 1
        j = 1

        while i < len(s):
            # end of t
            if  j >= len(t):
                break
            # s_i smaller than t_j -> add s_i to n
            if s[i] < t[j]:
                n.append(s[i])
                i += 1
            # s_i == t_j -> skip s_i and t_j, move to next t_j (this is the difference)
            elif s[i] == t[j]:
                i += 1
                j += 1
            else:
                # s_i larger than t_j, skip t_j
                j += 1

        # append rest of the elements of S
        if i < len(s) - 1:
            n = np.concatenate([n, s[i:]], axis=0)

        return n
            
    def find_background(self, cent_x, cent_y):
         
        if self.local_noise == 0:
            return 0
        if self.local_noise > 1:
            return self.local_noise

        large_noise_rect = get_pixels(cent_x, cent_y, self.A + 2*self.noise_dim, self.B + 2*self.noise_dim, self.alpha, self.image)[-1] # only Z pixels
        large_noise_rect = large_noise_rect[np.logical_not(np.isnan(large_noise_rect))]

        small_noise_rect = get_pixels(cent_x, cent_y, self.A + self.noise_dim, self.B + self.noise_dim, self.alpha, self.image)[-1] # only Z pixels
        small_noise_rect = small_noise_rect[np.logical_not(np.isnan(small_noise_rect))]

        in_between_frame = self.multiset_diff(large_noise_rect, small_noise_rect)

        local_noise_median = np.median(in_between_frame)

        return local_noise_median

    def execute(self) -> WrapperResult:

        _, _, data_Z = get_pixels(self.init_x, self.init_y, self.A, self.B, self.alpha, self.image)

        # check the content of the rectangle
        if np.nan in data_Z or data_Z == []:
            return WrapperResult(result=DatabaseItem(),
                              noise=-1,
                              log=None,
                              message='Null data',
                              code=1)
        if len(data_Z) < 4:
            return WrapperResult(result=DatabaseItem(),
                              noise=-1,
                              log=None,
                              message='Not enough data',
                              code=2)
        
        if np.max(data_Z) < self.pix_lim:
            return WrapperResult(result=DatabaseItem(),
                              noise=-1,
                              log=None,
                              message='Not pixel bright enough',
                              code=3)
        
        # find gravity centre
        c_x = self.init_x
        c_y = self.init_y
        iter  = 1
        
        # log iterations
        log = [[c_x, c_y, 0, 0, 0, 0, 0, 0, 0, 0, 0]]

        while True:

            current = find_gravity_centre(c_x, c_y, self.A, self.B, self.alpha, self.image, self.pix_prop)

            if current.center is None:
                return WrapperResult(result=DatabaseItem(cent_x=c_x, cent_y=c_y),
                              noise=-1,
                              log=log,
                              message='Could not find gravity centre',
                              code=4)

            # log attempt
            mu = np.mean(current.Z_pixels)
            v  = np.var(current.Z_pixels, ddof=1)
            s  = np.sqrt(v)
            sk = np.mean(((current.Z_pixels - mu)/s)**3)
            ku = np.mean(((current.Z_pixels - mu)/s)**4)

            log.append([current.center[0], current.center[1], 0, iter, np.sum(current.Z_pixels), mu,v,s,sk,ku])

            # position
            d_x  = c_x - current.center[0]
            d_y  = c_y - current.center[1]
            
            # distance from previous centre
            d = np.sqrt(d_x**2 + d_y**2)
            
            # if too close or too many iterations, exit loop
            if d < self.delta or iter > self.max_iter:
                break
            
            # new centre position
            c_x, c_y = current.center
            
            # count iteration
            iter += 1

        # stop if did not finish iteration in time
        if iter > self.max_iter:
            return WrapperResult(result=DatabaseItem(current.center[0], current.center[0], iter=iter),
                              noise=-1,
                              log=log,
                              message='Maximum number of iterations reached.',
                              code=5)

        # stop is finished too quickly
        if iter < self.min_iter:
            return WrapperResult(result=DatabaseItem(current.center[0], current.center[0], iter=iter),
                              noise=-1,
                              log=log,
                              message='Not enough iterations.',
                              code=6)

        grav_simple = deepcopy(current)
        cent_x, cent_y = grav_simple.center

        background = self.find_background(cent_x, cent_y)

        # fine centroiding with local noise removed
        if self.fine_iter > 0 and self.local_noise != 0:
            
            for _ in range(self.fine_iter):
                current = find_gravity_centre(current.center[0], current.center[1], self.A, self.B, self.alpha, self.image, self.pix_prop, background)
                cent_x, cent_y = current.center

            grav_simple = deepcopy(current)
            cent_x, cent_y = grav_simple.center

        # remove local background from local pixels (for calculation of statistics, IMAGE is not changed)
        grav_simple.Z_pixels = remove_negative(grav_simple.Z_pixels - background, val=10)

        # Definition for 1 pixel SNR (peak SNR) from Raab (2001) - Detecting and measuring faint point sources with a CCD, eq. 5
        # X_pixels, Y_pixels, Z_pixels = grav_simple[1:]
    
        signal = np.max(grav_simple.Z_pixels)
        noise  = np.sqrt(signal + background)
        snr    = signal / noise

        if snr < self.snr_lim:
            return WrapperResult(result=DatabaseItem(cent_x, cent_y, snr, iter, np.sum(grav_simple.Z_pixels)),
                              noise=background,
                              log=log,
                              message='Low signal-to-noise value.',
                              code=7)
        
        # stop if centre not right
        # maxpix_v = np.max(Z_pixels)
        maxpix_i = np.argmax(current.Z_pixels)
        maxpix_x = current.X_pixels[maxpix_i]
        maxpix_y = current.Y_pixels[maxpix_i]
        maxpix_d = np.sqrt((maxpix_x - current.center[0])**2 + (maxpix_y - current.center[1])**2)

        if self.is_point and maxpix_d > np.min([self.A, self.B])/2 :
            return WrapperResult(result=DatabaseItem(current.center[0], current.center[0],iter=iter),
                              noise=-1,
                              log=log,
                              message='Centre not right.',
                              code=8)


        # moments
        mu = np.mean(grav_simple.Z_pixels)
        v  =  np.var(grav_simple.Z_pixels, ddof=1)
        s  = np.sqrt(v)
        # skewness
        sk = np.mean(((grav_simple.Z_pixels - mu)/s)**3)
        # kurtosis
        ku = np.mean(((grav_simple.Z_pixels - mu)/s)**4)

        if self.fine_iter > 0 and self.local_noise != 0:
            log.append([current.center[0], current.center[1], 0, iter, np.sum(current.Z_pixels), mu, v, s, sk, ku])

        n_b = (2*self.A + 2*self.noise_dim) * (2*self.B + 2*self.noise_dim) - 2*self.A*2*self.B
        sum_brightness = np.sum(grav_simple.Z_pixels)
        bri_error = brightness_error(sum_brightness, background, len(grav_simple.Z_pixels), n_b)
        is_line = self.A != self.B

        return WrapperResult(result=DatabaseItem(cent_x, cent_y, snr, iter, sum_brightness, mu, v, s, sk, ku, background, bri_error=bri_error, is_line=is_line),
                             noise=background,
                             log=log,
                             message='OK',
                             code=0)

        
    
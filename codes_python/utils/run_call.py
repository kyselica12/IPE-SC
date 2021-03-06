def save_call(args):
    data = 'python3 ./main.py '
    data += '-F ' + str(args.input) + ' '
    data += '-A ' + str(args.width) + ' '
    data += '-B ' + str(args.height) + ' '
    data += '-C ' + str(args.angle) + ' '
    data += '-N ' + str(args.noise_dim) + ' '
    data += '-L ' + str(args.local_noise) + ' '
    data += '-D ' + str(args.delta) + ' '
    data += '-X ' + str(args.start_iter) + ' '
    data += '-M ' + str(args.max_iter) + ' '
    data += '-I ' + str(args.min_iter) + ' '
    data += '-S ' + str(args.snr_lim) + ' '
    data += '-Z ' + str(args.color) + ' '
    if args.model:
        data += '-E ' + str(args.model) + ' '
    data += '-O ' + str(args.output) + ' '
    data += '-Y ' + str(args.cent_pix_perc) + ' '
    data += '-G ' + str(args.init_noise_removal) + ' '
    data += '-H ' + str(args.fine_iter) + ' '
    data += '-K ' + str(args.method) + ' '
    data += '-P ' + str(args.parallel) + ' '
    data += '-V ' + str(args.verbose) + ' '
    data += '-J ' + str(args.json_config) + ' '
    data += '--sobel-threshold ' + str(args.sobel_threshold) + ' '
    data += '--bkg-iterations ' + str(args.bkg_iterations) + ' '
    data += '--fit-function ' + str(args.fit_function) + ' '
    data += '--psf ' + str(args.psf) + ' '
    data += '--centre-limit ' + str(args.centre_limit) + ' '
    data += '--match-limit ' + str(args.match_limit) + ' '
    data += '--pixscale ' + str(args.pixscale) + ' '




    with open(args.output+'.call', 'a') as f:
        print(data, file=f)

    with open(args.output + '.call.json', 'a') as f:
        data = args.to_json()
        print(data, file=f)

# print('configuring Arnold render settings Node! lops')
node = kwargs['node']

# Camera
node.parm('disableMotionBlur_control').set('set')

# File output
node.parm('productName').set('$RENDER/$HIPNAME/$OS/$OS.$F4.exr')
node.parm('camera').set('/Scene/CAM/camera1')

# File output/ Driver Options
node.parm('xn__arnolddriver_exrhalf_precision_control_y2bk').set('set')
node.parm('xn__arnolddriver_exrhalf_precision_xpbk').set(1)
node.parm('xn__arnolddriver_exrpreserve_layer_name_control_3bck').set('set')
node.parm('xn__arnolddriver_exrpreserve_layer_name_2xbk').set(1)
node.parm('xn__arnoldglobalenable_progressive_render_control_dfcg').set('set')
node.parm('xn__arnoldglobalenable_progressive_render_c1bg').set(1)

# File output/ AOVs
node.parm('layername1').set('C')
node.parm('aovprecision1').set('16')
node.parm('xn__arnoldglobalAA_samples_control_xpbg').set('set')
node.parm('xn__arnoldglobalAA_samples_wcbg').set(6)

# Rendering/ Samples
node.parm('xn__arnoldglobalenable_adaptive_sampling_control_qdcg').set('set')
node.parm('xn__arnoldglobalAA_samples_max_control_gwbg').set('set')
node.parm('xn__arnoldglobalAA_adaptive_threshold_control_u7bg').set('set')
node.parm('xn__arnoldglobalGI_diffuse_samples_control_y2bg').set('set')
node.parm('xn__arnoldglobalGI_specular_samples_control_l4bg').set('set')
node.parm('xn__arnoldglobalGI_transmission_samples_control_3bcg').set('set')
node.parm('xn__arnoldglobalGI_sss_samples_control_gwbg').set('set')
node.parm('xn__arnoldglobalGI_volume_samples_control_c1bg').set('set')

# Rendering/ Ray Depth
node.parm('xn__arnoldglobalGI_diffuse_depth_control_pzbg').set('set')
node.parm('xn__arnoldglobalGI_specular_depth_control_c1bg').set('set')
node.parm('xn__arnoldglobalGI_transmission_depth_control_u7bg').set('set')
node.parm('xn__arnoldglobalGI_volume_depth_control_2xbg').set('set')

# Rendering/ Textures
node.parm('xn__arnoldglobaltexture_auto_generate_tx_control_qdcg').set('set')
node.parm('xn__arnoldglobaltexture_auto_generate_tx_pzbg').set(0)
node.parm('xn__arnoldglobaltexture_use_existing_tx_control_3bcg').set('set')

# Rendering/ Diagnostics
node.parm('xn__arnoldglobalignore_motion_blur_control_y2bg').set('set')
node.parm('xn__arnoldgloballogverbosity_control_6sbgd').set('set')
node.parm('xn__arnoldgloballogverbosity_5fbgd').set('2')

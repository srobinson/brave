from brave.outputs.output import Output
import brave.config as config


class RTMPOutput(Output):
    '''
    For sending an output to a third-party RTMP server (such as Facebook Live).
    '''

    def permitted_props(self):
        return {
            **super().permitted_props(),
            'uri': {
                'type': 'str'
            },
            'width': {
                'type': 'int',
                'default': config.default_mixer_width()
            },
            'height': {
                'type': 'int',
                'default': config.default_mixer_height()
            }
        }

    def create_elements(self):
        '''
        Create the elements needed whether this is audio, video, or both
        '''

        self._create_initial_multiqueue()
        pipeline_string = 'flvmux name=mux streamable=true ! rtmpsink name=sink'

        if config.enable_video():
            # framerate=30/1 because Facebook Live and YouTube live want this framerate.
            # profile=baseline may be superflous but some have recommended it for Facebook
            video_caps = 'video/x-h264,framerate=30/1,profile=baseline,width=%d,height=%d,format=YUV' % \
                (self.props['width'], self.props['height'])

            # key-int-max=60 puts a keyframe every 2 seconds (60 as 2*framerate)
            pipeline_string = (pipeline_string +
                               ' intervideosrc name=intervideosrc ! videorate ! videoconvert ! videoscale ! ' +
                               ' x264enc name=video_encoder key-int-max=60 ! ' + video_caps +
                               ' ! h264parse ! queue ! mux.')

        if config.enable_audio():
            pipeline_string = pipeline_string + \
                ' interaudiosrc name=interaudiosrc ! audioconvert ! audioresample ! avenc_aac name=audio_encoder ! ' + \
                'aacparse ! audio/mpeg, mpegversion=4 ! queue ! mux.'

        self.logger.debug('Creating RTMP output with this pipeline: ' + pipeline_string)
        if not self.create_pipeline_from_string(pipeline_string):
            return False
        self.pipeline.get_by_name('sink').set_property('location', self.props['uri'] + ' live=1')

        if config.enable_video():
            self.intervideosrc = self.pipeline.get_by_name('intervideosrc')
            self.intervideosrc_src_pad = self.intervideosrc.get_static_pad('src')
            self.create_intervideosink_and_connections()

        if config.enable_audio():
            self.interaudiosrc = self.pipeline.get_by_name('interaudiosrc')
            self.interaudiosrc_src_pad = self.interaudiosrc.get_static_pad('src')
            self.create_interaudiosink_and_connections()

        self.logger.info('RTMP output now configured to send to ' + self.props['uri'])

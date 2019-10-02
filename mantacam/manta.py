#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2019-09-27
# @Filename: manta.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
# @Last modified by: José Sánchez-Gallego (gallegoj@uw.edu)
# @Last modified time: 2019-10-02 21:50:23

import asyncio
import os

import mantacam.cmanta as cmanta
import numpy
from yaml import Loader, load

from basecam.camera import Camera, CameraSystem

CONFIG_FILE = 'etc/cameras.yaml'


class CameraListObserver(cmanta.ICameraListObserver):
    """A camera list observer that callbacks on events.

    Parameters
    ----------
    on_camera_connected
        Callback function to call when a new camera is connected.
    on_camera_disconnected
        Callback function to call when a new camera is disconnected.

    """

    def __init__(self, on_camera_connected=None, on_camera_disconnected=None):

        self.on_camera_connected = on_camera_connected
        self.on_camera_disconnected = on_camera_disconnected

        super().__init__()

    def CameraListChanged(self, camera, reason):

        if reason == cmanta.UpdateTriggerType.UpdateTriggerPluggedIn:
            self.on_camera_connected(camera.GetID())
        elif reason == cmanta.UpdateTriggerType.UpdateTriggerPluggedOut:
            self.on_camera_disconnected(camera.GetID())


class FrameObserver(cmanta.IFrameObserver):
    """Notifies received frames."""

    def __init__(self, camera, queue):

        cmanta.IFrameObserver.__init__(self, camera)

        self.queue = queue

    def FrameReceived(self, frame):
        """Called when a new frame is available."""

        image = frame.GetImageInstance()
        array = numpy.array(image, dtype=numpy.uint8, copy=False)

        self.queue.put_nowait(array)

        # Requeue the frame
        self.camera.QueueFrame(frame)


class MantaCamera(Camera):
    """A Manta camera."""

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.camera = None
        self.frame_observer = None
        self.frames = []

        self.vimba_system = self.camera_system.vimba_system

        self.exposure_queue = asyncio.Queue()

    async def _connect_internal(self, **config_params):
        """Internal method to connect the camera."""

        assert 'connection_params' in config_params, \
            'connection_params missing from config_params.'

        device_id = config_params['connection_params'].get('device_id', None)
        if device_id is None:
            raise ValueError('device_id not present in connection_params')

        self.camera = self.vimba_system.GetCameraByID(device_id)
        self.camera.Open(cmanta.VmbAccessModeType.VmbAccessModeFull)

        self.frame_observer = FrameObserver(self.camera, self.exposure_queue)

        self.camera.GetFeatureByName('GVSPAdjustPacketSize').RunCommand()

        self.camera.GetFeatureByName('GVSPPacketSize').SetValueInt(1500)
        self.camera.GetFeatureByName('GevSCPSPacketSize').SetValueInt(1500)

        nPLS = self.camera.GetFeatureByName('PayloadSize').GetValueInt()

        self.frames = [cmanta.Frame(nPLS) for __ in range(3)]
        for frame in self.frames:
            frame.RegisterObserver(self.frame_observer)
            self.camera.AnnounceFrame(frame)

        self.camera.StartCapture()

        for frame in self.frames:
            self.camera.QueueFrame(frame)

        return True

    @property
    def _uid(self):
        """Get the unique identifier for the camera (e.g., serial number)."""

        if not self.camera:
            return None

        return self.camera.GetID()

    async def _expose_internal(self, exposure_time, shutter=True):
        """Internal method to handle camera exposures."""

        assert self.exposure_queue.empty(), \
            'exposure queue is not empty, cannot take new exposures.'

        assert self.connected, 'camera is not connected'

        self.camera.GetFeatureByName('AcquisitionMode').SetValueString('SingleFrame')
        self.camera.GetFeatureByName('ExposureTimeAbs').SetValueDouble(exposure_time * 1e6)

        self.camera.GetFeatureByName('AcquisitionStart').RunCommand()
        self.log('started exposing.')

        await asyncio.sleep(exposure_time)

        self.camera.GetFeatureByName('AcquisitionStop').RunCommand()
        self.log('finsihed exposing.')

        array = await asyncio.wait_for(self.exposure_queue.get(), timeout=1.0)

        return array

    async def _disconnect_internal(self):
        """Internal method to disconnect a camera."""

        self.camera.EndCapture()
        self.camera.Close()

        self.connected = False


class MantaSystem(CameraSystem):
    """Controls the camera system."""

    vimba_system = None
    camera_class = MantaCamera

    def __init__(self, loop=None):

        self.vimba_system = None
        self.camera_list_observer = None

        config = load(os.path.join(os.path.dirname(__file__), CONFIG_FILE), Loader=Loader)

        super().__init__(config=config, loop=loop)

    def setup_camera_system(self):
        """Setups the Manta camera system."""

        self.vimba_system = cmanta.VimbaSystem.GetInstance()
        self.vimba_system.Startup()

        self.camera_list_observer = CameraListObserver(
            on_camera_connected=self.on_camera_connected,
            on_camera_disconnected=self.on_camera_disconnected)
        self.vimba_system.RegisterCameraListObserver(self.camera_list_observer)

    def start_camera_poller(self):
        """Disable start_camera_poller for this camera system.

        Disables the camera poller since we will use the internal Vimba
        camera observer.

        """

        raise NotImplementedError('MantaSystem does not allow starting the camera poller.')

    def get_connected_cameras(self):
        """Returns a list of camera IDs for the cameras currently connected."""

        if self.vimba_system is None:
            return []

        cameras = self.vimba_system.GetCameras()
        ids = [camera.GetID() for camera in cameras]

        return ids

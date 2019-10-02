#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2019-09-27
# @Filename: manta.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
# @Last modified by: José Sánchez-Gallego (gallegoj@uw.edu)
# @Last modified time: 2019-10-01 18:18:59

import os

import mantacam.cmanta as cmanta
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


class MantaCamera(Camera):
    """A Manta camera."""

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.camera = None
        self.vimba_system = self.camera_system.vimba_system

    async def _connect_internal(self, **config_params):
        """Internal method to connect the camera."""

        assert 'connection_params' in config_params, \
            'connection_params missing from config_params.'

        device_id = config_params['connection_params'].get('device_id', None)
        if device_id is None:
            raise ValueError('device_id not present in connection_params')

        self.camera = self.vimba_system.GetCameraByID(device_id)
        self.camera.Open(cmanta.VmbAccessModeType.VmbAccessModeFull)

        return True

    @property
    def _uid(self):
        """Get the unique identifier for the camera (e.g., serial number)."""

        if not self.camera:
            return None

        return self.camera.GetID()

    async def _expose_internal(self, exposure_time, shutter=True):
        """Internal method to handle camera exposures."""

        pass

    async def _disconnect_internal(self):
        """Internal method to disconnect a camera."""

        pass


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

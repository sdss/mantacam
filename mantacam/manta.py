#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2019-07-25
# @Filename: manta.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
# @Last modified by: José Sánchez-Gallego (gallegoj@uw.edu)
# @Last modified time: 2019-08-03 19:39:20

import asyncio

import numpy

import mantacam.cmanta


class MyObserver(mantacam.cmanta.ICameraListObserver):

    def CameraListChanged(self, camera, reason):
        print(camera, reason)


class MyFrameObserver(mantacam.cmanta.IFrameObserver):

    # def __init__(self, camera):
    #     print(camera)
    #     mantacam.cmanta.IFrameObserver.__init__(self, camera)

    def FrameReceived(self, frame):
        image = frame.GetImageInstance()
        print(numpy.array(image, copy=False, dtype=numpy.uint8))
        self.camera.QueueFrame(frame)


my_observer = MyObserver()


async def main():

    vs = mantacam.cmanta.VimbaSystem.GetInstance()
    vs.Startup()

    camera = vs.GetCameras()[0]
    camera.Open(mantacam.cmanta.VmbAccessModeType.VmbAccessModeFull)

    my_frame_observer = MyFrameObserver(camera)

    feature = camera.GetFeatureByName('GVSPAdjustPacketSize')
    feature.RunCommand()

    feature = camera.GetFeatureByName('PayloadSize')
    nPLS = feature.GetValueInt()

    frames = [mantacam.cmanta.Frame(nPLS) for __ in range(3)]
    for frame in frames:
        frame.RegisterObserver(my_frame_observer)
        camera.AnnounceFrame(frame)

    camera.StartCapture()

    for frame in frames:
        camera.QueueFrame(frame)

    acq_start = camera.GetFeatureByName('AcquisitionStart')
    acq_stop = camera.GetFeatureByName('AcquisitionStop')

    acq_start.RunCommand()
    print('running')
    await asyncio.sleep(1)

    acq_stop.RunCommand()
    print('stopped')
    camera.EndCapture()

    while True:
        await asyncio.sleep(0.1)


if __name__ == '__main__':

    asyncio.run(main())

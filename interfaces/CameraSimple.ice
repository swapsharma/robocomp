
#ifndef CAMERASIMPLE_ICE
#define CAMERASIMPLE_ICE

module RoboCompCameraSimple
{
  exception HardwareFailedException { string what; };

  sequence<byte> ImgType;

  struct TImage
  {

    int width;
    int height;
    int depth;
    ImgType image;
  };

 
  interface CameraSimple
  {
    idempotent void getImage(out TImage im) throws HardwareFailedException;
  };
};

#endif

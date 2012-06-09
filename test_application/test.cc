#include <iostream>
#include <stdlib.h>

// Additional Headers required for ISIS
#include <FileName.h>
#include <CameraFactory.h>
#include <ProjectionFactory.h>
#include <Camera.h>
#include <Pvl.h>
#include <AlphaCube.h>
#include <CameraFocalPlaneMap.h>
#include <CameraDetectorMap.h>
#include <CameraDistortionMap.h>
#include <Projection.h>
#include <Latitude.h>
#include <Longitude.h>
#include <Distance.h>

int main( int argc, char **argv ) {

  if ( !getenv("ISISROOT") ) {
    std::cerr << "Please define ISISROOT as the directory contain the lib directory that holds all ISIS libraries." << std::endl;
    return 1;
  }

  if ( !getenv("ISIS3DATA") ) {
    std::cerr << "Please define ISIS3DATA as the directory that contains base and mission specific kernels." << std::endl;
    return 1;
  }

  if ( argc != 2 ) {
    std::cerr << "Please provide a cube file as the first argument." << std::endl;
    return 1;
  }

  Isis::FileName cubefile( argv[1] );
  Isis::Pvl label;
  label.Read( cubefile.expanded() );
  Isis::Camera* cam = Isis::CameraFactory::Create( label );
  Isis::AlphaCube alphacube( label );

  std::cout << "CameraType: " << cam->GetCameraType() << "\n";

  return 0;
}

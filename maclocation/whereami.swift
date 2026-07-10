// macOS CoreLocation helper for iPhone Spoofer.
// Reads the Mac's real location and writes it to the output file given as argv[1]
// (falls back to /tmp/iphonespoofer-maclocation.txt). Must run inside a signed
// .app bundle with NSLocationUsageDescription — a bare CLI gets kCLErrorDomain
// error 1 with no TCC prompt.
//
// Output file formats (single line):
//   OK <lat> <lon> acc=<meters>
//   DENIED <status>
//   TIMEOUT
import CoreLocation
import Foundation

let OUT = CommandLine.arguments.count > 1
    ? CommandLine.arguments[1]
    : "/tmp/iphonespoofer-maclocation.txt"

func w(_ s: String) { try? s.write(toFile: OUT, atomically: true, encoding: .utf8) }

final class Locator: NSObject, CLLocationManagerDelegate {
    let mgr = CLLocationManager()
    var started = false

    func begin() {
        mgr.delegate = self
        mgr.desiredAccuracy = kCLLocationAccuracyBest
        evaluate(mgr.authorizationStatus)
    }

    func evaluate(_ s: CLAuthorizationStatus) {
        switch s {
        case .notDetermined:
            mgr.requestWhenInUseAuthorization()
        case .authorizedAlways, .authorized:
            if !started { started = true; mgr.startUpdatingLocation() }
        case .denied, .restricted:
            w("DENIED \(s.rawValue)"); exit(3)
        @unknown default:
            break
        }
    }

    func locationManagerDidChangeAuthorization(_ m: CLLocationManager) {
        evaluate(m.authorizationStatus)
    }

    func locationManager(_ m: CLLocationManager, didUpdateLocations locs: [CLLocation]) {
        if let l = locs.last {
            w("OK \(l.coordinate.latitude) \(l.coordinate.longitude) acc=\(l.horizontalAccuracy)")
            exit(0)
        }
    }

    func locationManager(_ m: CLLocationManager, didFailWithError e: Error) {
        // Transient errors are expected while waiting for authorization / first fix — ignore.
    }
}

let loc = Locator()
loc.begin()
DispatchQueue.global().asyncAfter(deadline: .now() + 40) { w("TIMEOUT"); exit(4) }
RunLoop.main.run()

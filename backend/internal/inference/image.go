package inference

import (
	"fmt"
	"image"
	_ "image/jpeg"
	"os"
)

// The goal of this module is to preprocess the image
// before model runtime

// NOTE: This currently only accept 640x640 images for the sake of testing.
// TODO: Generalize image size and file formats.

// LoadImage reads a JPEG image and copies its pixels into detector's input tensor
func (d *Detector) LoadImage(imagePath string) error {
	file, err := os.Open(imagePath)
	if err != nil {
		return err
	}
	defer file.Close() // Defer is so cool. the more you learn!

	img, _, err := image.Decode(file)
	if err != nil {
		return err
	}

	bounds := img.Bounds()
	if bounds.Dx() != 640 || bounds.Dy() != 640 {
		return fmt.Errorf("expected a 640x640 image, got %dx%d instead", bounds.Dx(), bounds.Dy())
	}

	pixels := d.input.GetData()
	planeSize := 640 * 640

	// Model expects channel-first data: [1, 3, 640, 640]
	for y := 0; y < 640; y++ {
		for x := 0; x < 640; x++ {
			r, g, b, _ := img.At(bounds.Min.X+x, bounds.Min.Y+y).RGBA()

			i := y*640 + x

			// Convert 16 bit channel values to [0, 1] float32 values
			pixels[i] = float32(r) / 65535.0
			pixels[planeSize+i] = float32(g) / 65535.0
			pixels[2*planeSize+i] = float32(b) / 65535.0
		}
	}

	return nil
}

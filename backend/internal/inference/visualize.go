package inference

import (
	"fmt"
	"image"
	"image/color"
	"image/draw"
	"image/jpeg"
	"os"
)

// SaveVisualization draws a bounding box and confidence label onto an image
func SaveVisualization(
	imagePath string,
	outputPath string,
	x, y, w, h float32,
	confidence float32,
) error {
	// Open and decode original image
	file, err := os.Open(imagePath)
	if err != nil {
		return err
	}
	defer file.Close()

	img, _, err := image.Decode(file)
	if err != nil {
		return err
	}

	// Make a writeable copy of input image
	bounds := img.Bounds()
	canvas := image.NewRGBA(bounds)
	draw.Draw(canvas, bounds, img, bounds.Min, draw.Src)

	// Inperpret x and y as the box center
	left := int(x - w/2)
	top := int(y - h/2)
	right := int(x + w/2)
	bottom := int(y + h/2)

	// Use red to make the box easy to spot
	red := color.RGBA{R: 255, G: 0, B: 0, A: 255}

	// Draw rectangle w 3 pixel border
	for t := 0; t < 3; t++ {
		for px := left; px <= right; px++ {
			setPixel(canvas, px, top+t, red)
			setPixel(canvas, px, bottom-t, red)
		}
		for py := top; py <= bottom; py++ {
			setPixel(canvas, left+t, py, red)
			setPixel(canvas, right-t, py, red)
		}
	}

	// Save annotated image as JPEG
	out, err := os.Create(outputPath)
	if err != nil {
		return nil
	}
	defer out.Close()

	if err := jpeg.Encode(out, canvas, &jpeg.Options{Quality: 95}); err != nil {
		return err
	}

	fmt.Printf("Saved visualization to %s\n", outputPath)
	return nil
}

func setPixel(img *image.RGBA, x, y int, c color.RGBA) {
	if image.Pt(x, y).In(img.Bounds()) {
		img.SetRGBA(x, y, c)
	}
}

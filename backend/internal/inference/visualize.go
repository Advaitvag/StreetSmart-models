package inference

import (
	"fmt"
	"image"
	"image/color"
	"image/draw"
	"image/jpeg"
	"os"
)

type Prediction struct {
	X, Y, W, H float32
	Score      float32
	Index      int
}

func SaveVisualization(
	imagePath string,
	outputPath string,
	predictions []Prediction,
) error {
	file, err := os.Open(imagePath)
	if err != nil {
		return err
	}
	defer file.Close()

	img, _, err := image.Decode(file)
	if err != nil {
		return err
	}

	bounds := img.Bounds()
	canvas := image.NewRGBA(bounds)
	draw.Draw(canvas, bounds, img, bounds.Min, draw.Src)

	// Cycle through colors so overlapping boxes are easier to distinguish.
	colors := []color.RGBA{
		{R: 255, G: 0, B: 0, A: 255},
		{R: 0, G: 255, B: 0, A: 255},
		{R: 0, G: 100, B: 255, A: 255},
		{R: 255, G: 165, B: 0, A: 255},
		{R: 255, G: 0, B: 255, A: 255},
	}

	for i, p := range predictions {
		c := colors[i%len(colors)]

		// Treat x and y as the box center.
		left := int(p.X - p.W/2)
		top := int(p.Y - p.H/2)
		right := int(p.X + p.W/2)
		bottom := int(p.Y + p.H/2)

		// Draw a 3-pixel border.
		for t := 0; t < 3; t++ {
			for px := left; px <= right; px++ {
				setPixel(canvas, px, top+t, c)
				setPixel(canvas, px, bottom-t, c)
			}
			for py := top; py <= bottom; py++ {
				setPixel(canvas, left+t, py, c)
				setPixel(canvas, right-t, py, c)
			}
		}

		fmt.Printf(
			"Box %d: index=%d score=%.4f\n",
			i+1, p.Index, p.Score,
		)
	}

	out, err := os.Create(outputPath)
	if err != nil {
		return err
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

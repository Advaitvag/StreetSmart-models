package main

import (
	"fmt"
	"log"
	"os"
	"runtime"
	"sort"

	ort "github.com/yalue/onnxruntime_go"

	"streetsmart-backend/internal/inference"
)

func libPath() string {
	if v := os.Getenv("ORT_LIB_PATH"); v != "" {
		return v
	}
	if runtime.GOOS == "linux" {
		return "lib/libonnxruntime.so.1.29.0"
	}
	if runtime.GOOS == "windows" {
		return "lib/onnxruntime.dll"
	}
	log.Fatalf("unsupported GOOS: %s (only windows + linux)", runtime.GOOS)
	return ""
}

func main() {
	fmt.Println("Initializing ONNX Runtime...")

	ort.SetSharedLibraryPath(libPath())

	err := ort.InitializeEnvironment()
	if err != nil {
		log.Fatal(err)
	}
	defer ort.DestroyEnvironment()

	fmt.Println("ONNX Runtime initialized successfully!")

	detector, err := inference.NewDetector("models/pothole.onnx")
	if err != nil {
		log.Fatal("Failed to load detector: ", err)
	}
	defer detector.Close()

	fmt.Println("Pothole detector loaded successfully")

	if err := detector.LoadImage("test_inputs/pothole.jpg"); err != nil {
		log.Fatal("Failed to load image: ", err)
	}

	predictions, err := detector.Run()
	if err != nil {
		log.Fatal("Inference failed: ", err)
	}

	const numCandidates = 8400

	scores := predictions[4*numCandidates : 5*numCandidates]

	indices := make([]int, len(scores))
	for i := range indices {
		indices[i] = i
	}

	sort.Slice(indices, func(i, j int) bool {
		return scores[indices[i]] > scores[indices[j]]
	})

	limit := 10
	if len(indices) < limit {
		limit = len(indices)
	}

	topPredictions := make([]inference.Prediction, 0, limit)

	for rank := 0; rank < limit; rank++ {
		i := indices[rank]

		topPredictions = append(topPredictions, inference.Prediction{
			X:     predictions[i],
			Y:     predictions[numCandidates+i],
			W:     predictions[2*numCandidates+i],
			H:     predictions[3*numCandidates+i],
			Score: scores[i],
			Index: i,
		})
	}

	err = inference.SaveVisualization(
		"test_inputs/pothole.jpg",
		"test_inputs/pothole-top10.jpg",
		topPredictions,
	)
	if err != nil {
		log.Fatal("Failed to save visualization: ", err)
	}

	fmt.Printf("Inference succeeded! Received %d values.\n", len(predictions))
	fmt.Printf("First 10 values: %v\n", predictions[:10])
}

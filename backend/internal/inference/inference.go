package inference

import (
	ort "github.com/yalue/onnxruntime_go"
)

type Detector struct {
	session *ort.AdvancedSession
}

func NewDetector(modelPath string) (*Detector, error) {
	return nil, nil
}

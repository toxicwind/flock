package astmatrix

import "fmt"

type MockMonitor struct {
	name string
}

func NewMockMonitor(name string) *MockMonitor {
	return &MockMonitor{name: name}
}

func (m *MockMonitor) Infof(format string, args ...interface{}) {
	fmt.Printf("[INFO] "+format+"\n", args...)
}

func (m *MockMonitor) Warnf(format string, args ...interface{}) {
	fmt.Printf("[WARN] "+format+"\n", args...)
}

func (m *MockMonitor) Debugf(format string, args ...interface{}) {
	fmt.Printf("[DEBUG] "+format+"\n", args...)
}

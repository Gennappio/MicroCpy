"""
Performance monitoring and profiling for MicroC 2.0

Provides comprehensive performance tracking, profiling, and optimization tools.
"""

import time
import psutil
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, deque
import sys
from pathlib import Path

# Add interfaces to path
sys.path.insert(0, str(Path(__file__).parent.parent))
# Hook system removed - using direct function calls

@dataclass
class PerformanceMetrics:
    """Immutable performance metrics snapshot"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    process_times: Dict[str, float] = field(default_factory=dict)
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'timestamp': self.timestamp,
            'cpu_percent': self.cpu_percent,
            'memory_mb': self.memory_mb,
            'memory_percent': self.memory_percent,
            'process_times': self.process_times.copy(),
            'custom_metrics': self.custom_metrics.copy()
        }

@dataclass
class ProfileEntry:
    """Single profiling entry"""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self, metadata: Optional[Dict[str, Any]] = None):
        """Mark entry as finished"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        if metadata:
            self.metadata.update(metadata)

class PerformanceProfiler:
    """Context manager for profiling code blocks"""
    
    def __init__(self, monitor: 'PerformanceMonitor', name: str, metadata: Optional[Dict[str, Any]] = None):
        self.monitor = monitor
        self.name = name
        self.metadata = metadata or {}
        self.entry = None
    
    def __enter__(self):
        self.entry = self.monitor.start_profile(self.name, self.metadata)
        return self.entry
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.entry:
            self.monitor.end_profile(self.name)

class PerformanceMonitor:
    """
    Comprehensive performance monitoring system
    
    Tracks CPU, memory, timing, and custom metrics with profiling capabilities.
    """
    
    def __init__(self, custom_functions_module=None, max_history=1000):
        # Hook system removed
        self.max_history = max_history
        
        # Performance history
        self.metrics_history: deque = deque(maxlen=max_history)
        self.profile_history: Dict[str, List[ProfileEntry]] = defaultdict(list)
        
        # Active profiles
        self.active_profiles: Dict[str, ProfileEntry] = {}
        
        # Process monitoring
        self.process = psutil.Process()
        self.monitoring_enabled = True
        self.monitoring_interval = 1.0  # seconds
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()
        
        # Performance thresholds
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 80.0,
            'memory_mb': 1000.0,
            'process_time': 1.0  # seconds
        }
        
        # Alerts
        self.alerts_enabled = True
        self.alert_callbacks: List[Callable] = []
        
        # Statistics
        self.stats = {
            'total_profiles': 0,
            'total_alerts': 0,
            'monitoring_start_time': time.time()
        }
    
    def start_monitoring(self, interval: float = 1.0):
        """Start background performance monitoring"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
        
        self.monitoring_interval = interval
        self.stop_monitoring.clear()
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
    
    def stop_monitoring_thread(self):
        """Stop background monitoring"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.stop_monitoring.set()
            self.monitoring_thread.join(timeout=2.0)
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while not self.stop_monitoring.wait(self.monitoring_interval):
            if self.monitoring_enabled:
                try:
                    metrics = self.capture_metrics()
                    self.metrics_history.append(metrics)
                    self._check_thresholds(metrics)
                except Exception as e:
                    # Don't let monitoring errors crash the simulation
                    print(f"Performance monitoring error: {e}")
    
    def capture_metrics(self) -> PerformanceMetrics:
        """Capture current performance metrics"""
        try:
            # Get system metrics
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = self.process.memory_percent()
            
            # Get process times
            process_times = {}
            for name, entries in self.profile_history.items():
                if entries:
                    recent_entries = entries[-10:]  # Last 10 entries
                    avg_time = sum(e.duration for e in recent_entries if e.duration) / len(recent_entries)
                    process_times[name] = avg_time
            
            # No custom metrics - hook system removed
            custom_metrics = {}
            
            return PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                process_times=process_times,
                custom_metrics=custom_metrics or {}
            )
        except Exception as e:
            # Return minimal metrics on error
            return PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=0.0,
                memory_mb=0.0,
                memory_percent=0.0
            )
    
    def start_profile(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> ProfileEntry:
        """Start profiling a named operation"""
        entry = ProfileEntry(
            name=name,
            start_time=time.time(),
            metadata=metadata or {}
        )
        self.active_profiles[name] = entry
        self.stats['total_profiles'] += 1
        return entry
    
    def end_profile(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[ProfileEntry]:
        """End profiling a named operation"""
        if name not in self.active_profiles:
            return None
        
        entry = self.active_profiles.pop(name)
        entry.finish(metadata)
        
        # Store in history
        self.profile_history[name].append(entry)
        
        # Keep only recent entries
        if len(self.profile_history[name]) > self.max_history:
            self.profile_history[name] = self.profile_history[name][-self.max_history:]
        
        # Check thresholds
        if entry.duration and entry.duration > self.thresholds['process_time']:
            self._trigger_alert('process_time', {
                'process': name,
                'duration': entry.duration,
                'threshold': self.thresholds['process_time']
            })
        
        return entry
    
    def profile(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> PerformanceProfiler:
        """Create a profiling context manager"""
        return PerformanceProfiler(self, name, metadata)
    
    def _check_thresholds(self, metrics: PerformanceMetrics):
        """Check if metrics exceed thresholds"""
        if not self.alerts_enabled:
            return
        
        if metrics.cpu_percent > self.thresholds['cpu_percent']:
            self._trigger_alert('cpu_percent', {
                'value': metrics.cpu_percent,
                'threshold': self.thresholds['cpu_percent']
            })
        
        if metrics.memory_percent > self.thresholds['memory_percent']:
            self._trigger_alert('memory_percent', {
                'value': metrics.memory_percent,
                'threshold': self.thresholds['memory_percent']
            })
        
        if metrics.memory_mb > self.thresholds['memory_mb']:
            self._trigger_alert('memory_mb', {
                'value': metrics.memory_mb,
                'threshold': self.thresholds['memory_mb']
            })
    
    def _trigger_alert(self, alert_type: str, data: Dict[str, Any]):
        """Trigger a performance alert"""
        self.stats['total_alerts'] += 1
        
        alert_data = {
            'type': alert_type,
            'timestamp': time.time(),
            'data': data
        }
        
        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                print(f"Alert callback error: {e}")
        
        # No custom alert handling - hook system removed
    
    def add_alert_callback(self, callback: Callable):
        """Add an alert callback function"""
        self.alert_callbacks.append(callback)
    
    def set_threshold(self, metric: str, value: float):
        """Set a performance threshold"""
        self.thresholds[metric] = value
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        current_time = time.time()
        uptime = current_time - self.stats['monitoring_start_time']
        
        stats = {
            'uptime_seconds': uptime,
            'total_profiles': self.stats['total_profiles'],
            'total_alerts': self.stats['total_alerts'],
            'active_profiles': len(self.active_profiles),
            'metrics_history_size': len(self.metrics_history),
            'thresholds': self.thresholds.copy(),
            'monitoring_enabled': self.monitoring_enabled
        }
        
        # Add current metrics
        if self.metrics_history:
            latest_metrics = self.metrics_history[-1]
            stats['current_metrics'] = latest_metrics.to_dict()
        
        # Add profile statistics
        profile_stats = {}
        for name, entries in self.profile_history.items():
            if entries:
                durations = [e.duration for e in entries if e.duration]
                if durations:
                    profile_stats[name] = {
                        'count': len(entries),
                        'avg_duration': sum(durations) / len(durations),
                        'min_duration': min(durations),
                        'max_duration': max(durations),
                        'total_duration': sum(durations)
                    }
        stats['profile_statistics'] = profile_stats
        
        return stats
    
    def get_metrics_history(self, last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get metrics history"""
        history = list(self.metrics_history)
        if last_n:
            history = history[-last_n:]
        return [m.to_dict() for m in history]
    
    def get_profile_history(self, process_name: str, last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get profile history for a specific process"""
        entries = self.profile_history[process_name]
        if last_n:
            entries = entries[-last_n:]
        
        return [{
            'name': e.name,
            'start_time': e.start_time,
            'end_time': e.end_time,
            'duration': e.duration,
            'metadata': e.metadata
        } for e in entries]
    
    def reset_statistics(self):
        """Reset all statistics and history"""
        self.metrics_history.clear()
        self.profile_history.clear()
        self.active_profiles.clear()
        self.stats = {
            'total_profiles': 0,
            'total_alerts': 0,
            'monitoring_start_time': time.time()
        }
    
    def enable_monitoring(self, enabled: bool = True):
        """Enable or disable monitoring"""
        self.monitoring_enabled = enabled
    
    def enable_alerts(self, enabled: bool = True):
        """Enable or disable alerts"""
        self.alerts_enabled = enabled
    
    def __del__(self):
        """Cleanup on deletion"""
        self.stop_monitoring_thread()

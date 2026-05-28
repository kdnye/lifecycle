/* FSI Asset Scanner — camera (html5-qrcode) + BLE (Web Bluetooth) + AJAX lookup */
(function () {
  'use strict';

  var SCAN_ENDPOINT = '/inventory/scan';
  var NEW_ASSET_PATH = '/inventory/new';

  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
  }

  function lookupTag(tag, widget) {
    var preview = widget.querySelector('.fsi-scanner-preview');
    var status  = widget.querySelector('[data-scanner-status]');

    status.textContent = 'Looking up “' + tag + '”…';
    status.style.display = 'block';
    preview.style.display = 'none';

    fetch(SCAN_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({ tag: tag }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        status.style.display = 'none';
        preview.style.display = 'block';
        if (data.found) {
          preview.innerHTML =
            '<i class="bi bi-check-circle text-success"></i> ' +
            'Asset found: <strong>' + (data.it_asset_tag || data.serial_number || '#' + data.id) + '</strong> ' +
            '(' + data.status + ') &mdash; opening asset page…';
          window.location.assign(data.detail_url);
        } else {
          preview.innerHTML =
            '<i class="bi bi-exclamation-triangle text-warning"></i> ' +
            'Warning not in system: would you like to create a new asset?';
          if (window.confirm('Warning not in system: would you like to create a new asset?')) {
            window.location.assign(NEW_ASSET_PATH + '?asset_number=' + encodeURIComponent(tag));
          }
        }
      })
      .catch(function () {
        status.style.display = 'none';
        preview.textContent = 'Lookup failed. Check network connection.';
        preview.style.display = 'block';
      });
  }


  function getCameraSelect(widget) {
    return widget ? widget.querySelector('[data-camera-select]') : null;
  }

  function getCameraStartConfig(select) {
    if (select && select.value) {
      return select.value;
    }
    return { facingMode: 'environment' };
  }

  function describeCamera(camera, index) {
    return camera.label || ('Camera ' + (index + 1));
  }

  function setCameraSelectState(select, cameras) {
    if (!select) return;

    var currentValue = select.value;
    select.innerHTML = '';

    var fallbackOption = document.createElement('option');
    fallbackOption.value = '';
    fallbackOption.textContent = 'Default rear camera';
    select.appendChild(fallbackOption);

    cameras.forEach(function (camera, index) {
      var option = document.createElement('option');
      option.value = camera.id;
      option.textContent = describeCamera(camera, index);
      select.appendChild(option);
    });

    if (currentValue) {
      for (var i = 0; i < select.options.length; i++) {
        if (select.options[i].value === currentValue) {
          select.value = currentValue;
          break;
        }
      }
    }

    select.disabled = cameras.length === 0;
  }

  function emptyCameraListResult() {
    return {
      then: function (callback) {
        if (typeof callback === 'function') callback([]);
        return this;
      },
      'catch': function () {
        return this;
      }
    };
  }

  function populateCameraSelect(select, status) {
    if (!select) return emptyCameraListResult();

    if (!window.Html5Qrcode || typeof Html5Qrcode.getCameras !== 'function') {
      select.disabled = true;
      if (status) {
        status.textContent = 'Camera selection is unavailable until the scanner library loads.';
        status.style.display = 'block';
      }
      return emptyCameraListResult();
    }

    return Html5Qrcode.getCameras()
      .then(function (cameras) {
        setCameraSelectState(select, cameras || []);
        return cameras || [];
      })
      .catch(function (err) {
        select.disabled = true;
        if (status) {
          status.textContent = 'Unable to list cameras. Browser permission may be required: ' + (err && err.message ? err.message : err);
          status.style.display = 'block';
        }
        return [];
      });
  }

  window.FsiScannerCameras = {
    getCameraStartConfig: getCameraStartConfig,
    populateCameraSelect: populateCameraSelect,
  };

  function fillTargetField(widget, value) {
    var fieldId = widget.dataset.fieldId || 'it_asset_tag';
    var input = document.getElementById(fieldId);
    if (input) {
      input.value = value;
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }

  function initCameraScanner(widget) {
    var btn      = widget.querySelector('[data-action="camera-scan"]');
    var readerId = 'qr-reader-' + widget.id;
    var readerEl = document.getElementById(readerId);
    if (!btn || !readerEl) return;

    var scanner = null;
    var scanning = false;
    var cameraSelect = getCameraSelect(widget);
    var status = widget.querySelector('[data-scanner-status]');

    populateCameraSelect(cameraSelect, status);

    btn.addEventListener('click', function () {
      if (scanning) {
        scanner.stop().catch(function () {});
        scanning = false;
        btn.innerHTML = '<i class="bi bi-qr-code-scan"></i> Scan Barcode / QR';
        return;
      }
      if (typeof Html5Qrcode === 'undefined') {
        alert('html5-qrcode library not loaded.');
        return;
      }
      scanner  = new Html5Qrcode(readerId);
      scanning = true;
      btn.innerHTML = '<i class="bi bi-stop-circle"></i> Stop Scanner';
      scanner.start(
        getCameraStartConfig(cameraSelect),
        { fps: 10, qrbox: { width: 250, height: 250 } },
        function onScanSuccess(decodedText) {
          scanner.stop().catch(function () {});
          scanning = false;
          btn.innerHTML = '<i class="bi bi-qr-code-scan"></i> Scan Barcode / QR';
          fillTargetField(widget, decodedText);
          lookupTag(decodedText, widget);
        },
        null
      ).catch(function (err) {
        scanning = false;
        btn.innerHTML = '<i class="bi bi-qr-code-scan"></i> Scan Barcode / QR';
        var status = widget.querySelector('[data-scanner-status]');
        if (status) {
          status.textContent = 'Camera error: ' + err;
          status.style.display = 'block';
        }
      });
    });
  }

  function initBleScanner(widget) {
    var btn = widget.querySelector('[data-action="ble-scan"]');
    if (!btn) return;

    if (!navigator.bluetooth) {
      btn.style.display = 'none';
      return;
    }

    btn.addEventListener('click', function () {
      var status = widget.querySelector('[data-scanner-status]');
      if (status) {
        status.textContent = 'Requesting BLE device…';
        status.style.display = 'block';
      }
      navigator.bluetooth
        .requestDevice({ acceptAllDevices: true })
        .then(function (device) {
          var tagValue = device.name || device.id;
          if (status) status.style.display = 'none';
          fillTargetField(widget, tagValue);
          lookupTag(tagValue, widget);
        })
        .catch(function (err) {
          if (status) {
            status.textContent = 'BLE cancelled or error: ' + err.message;
            status.style.display = 'block';
          }
        });
    });
  }

  function initWidget(widget) {
    initCameraScanner(widget);
    initBleScanner(widget);
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.fsi-scanner-widget').forEach(initWidget);
  });
})();

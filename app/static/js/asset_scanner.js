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
        { facingMode: 'environment' },
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

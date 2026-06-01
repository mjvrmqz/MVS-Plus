                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": host if host.startswith(".") else "." + host.lstrip("."),
                    "path": path if path else "/",
                    "secure": bool(secure),
                    "httpOnly": bool(httponly),
                })

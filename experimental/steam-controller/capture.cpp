// Read-only capture of native controller state. No pairing, settings or
// outputs.
#include "triton.hpp"
#include <cerrno>
#include <chrono>
#include <cstring>
#include <fcntl.h>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <linux/hidraw.h>
#include <poll.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <vector>
int main(int argc, char **argv) {
  unsigned seconds = 20;
  if (argc == 2) {
    try {
      seconds = std::stoul(argv[1]);
    } catch (...) {
      return 2;
    }
  }
  if (argc > 2 || !seconds || seconds > 300) {
    std::cerr << "Usage: capture [seconds 1..300]\n";
    return 2;
  }
  std::vector<pollfd> fds;
  std::vector<std::string> paths;
  for (const auto &entry : std::filesystem::directory_iterator("/dev")) {
    if (entry.path().filename().string().rfind("hidraw", 0) != 0)
      continue;
    int fd = open(entry.path().c_str(), O_RDONLY | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0)
      continue;
    hidraw_devinfo info{};
    if (ioctl(fd, HIDIOCGRAWINFO, &info) == 0 && info.vendor == 0x28de &&
        info.product >= 0x1302 && info.product <= 0x1305) {
      fds.push_back({fd, POLLIN, 0});
      paths.push_back(entry.path());
    } else
      close(fd);
  }
  if (fds.empty()) {
    std::cerr << "No readable Steam Controller endpoint. Check connection and "
                 "hidraw permissions.\n";
    return 3;
  }
  const auto start = std::chrono::steady_clock::now();
  unsigned count = 0;
  std::cerr << "Listening without changing controller settings for " << seconds
            << " seconds.\n";
  while (std::chrono::steady_clock::now() - start <
         std::chrono::seconds(seconds)) {
    int n = poll(fds.data(), fds.size(), 100);
    if (n < 0) {
      if (errno == EINTR)
        continue;
      std::cerr << strerror(errno) << '\n';
      break;
    }
    for (unsigned i = 0; i < fds.size(); ++i) {
      if (fds[i].revents & (POLLHUP | POLLERR | POLLNVAL)) {
        close(fds[i].fd);
        fds[i].fd = -1;
        continue;
      }
      if (!(fds[i].revents & POLLIN))
        continue;
      std::array<std::uint8_t, 64> b{};
      auto size = read(fds[i].fd, b.data(), b.size());
      if (size <= 0)
        continue;
      auto state = triton::decode({b.data(), static_cast<std::size_t>(size)});
      if (!state)
        continue;
      auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
                    std::chrono::steady_clock::now() - start)
                    .count();
      std::cout << "{\"elapsed_ns\":" << ns << ",\"endpoint\":\"" << paths[i]
                << "\",\"report\":\"";
      for (int j = 0; j < size; ++j)
        std::cout << std::hex << std::setw(2) << std::setfill('0')
                  << unsigned(b[j]);
      std::cout << std::dec << "\"}\n";
      ++count;
    }
  }
  for (auto &fd : fds)
    if (fd.fd >= 0)
      close(fd.fd);
  std::cerr << count << " native state reports captured.\n";
  return count ? 0 : 4;
}

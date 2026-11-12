// wireplane_products.cxx -- gallery reader that flattens art products into plain
// arrays for extract_wireplane_h5.py. Compiled with ACLiC inside the uboonecode
// environment (ROOT.gROOT.ProcessLine(".L wireplane_products.cxx+")).
//
// Pattern: load<X>(tag) fetches the product for the current event and returns the
// number of rows; fill<X>(addresses...) copies into buffers allocated by the caller
// (numpy arrays; the address is array.ctypes.data).
#include "gallery/Event.h"
#include "canvas/Utilities/InputTag.h"
#include "canvas/Persistency/Common/Assns.h"
#include "canvas/Persistency/Provenance/EventAuxiliary.h"
#include "lardataobj/RawData/RawDigit.h"
#include "lardataobj/RawData/raw.h"
#include "lardataobj/RecoBase/Wire.h"
#include "lardataobj/Simulation/SimChannel.h"
#include "lardataobj/Simulation/SimEnergyDeposit.h"
#include "lardataobj/Simulation/GeneratedParticleInfo.h"
#include "nusimdata/SimulationBase/MCParticle.h"
#include "nusimdata/SimulationBase/MCTruth.h"

#include <map>
#include <string>
#include <vector>
#include <cstring>

class WireplaneReader {
public:
  explicit WireplaneReader(std::string fname) : fEv(std::vector<std::string>{fname}) {}

  long long nEvents() const { return fEv.numberOfEventsInFile(); }
  void goTo(long long i) { fEv.goToEntry(i); clear(); }
  unsigned run() const { return fEv.eventAuxiliary().run(); }
  unsigned subrun() const { return fEv.eventAuxiliary().subRun(); }
  unsigned event() const { return fEv.eventAuxiliary().event(); }

  // ---- raw::RawDigit ------------------------------------------------------
  // returns number of digits; nChannels()/nTicks() describe the dense array
  long long loadRawDigits(std::string label, std::string inst, std::string proc) {
    fRD = fEv.getValidHandle<std::vector<raw::RawDigit>>(art::InputTag(label, inst, proc)).product();
    fNch = 0; fNticks = 0;
    for (auto const& d : *fRD) {
      if (d.Channel() + 1 > fNch) fNch = d.Channel() + 1;
      if (d.Samples() > fNticks) fNticks = d.Samples();
    }
    return fRD->size();
  }
  unsigned nChannels() const { return fNch; }
  unsigned nTicks() const { return fNticks; }
  // adc: int16 [nch*nticks] row = channel; pedestal,sigma: float32 [nch]; present: uint8 [nch]
  void fillRawDigits(ULong64_t adc_, ULong64_t ped_, ULong64_t sigma_, ULong64_t present_) const {
    short* adc = (short*)adc_; float* ped = (float*)ped_; float* sig = (float*)sigma_;
    unsigned char* present = (unsigned char*)present_;
    std::vector<short> buf;
    for (auto const& d : *fRD) {
      const size_t ch = d.Channel();
      buf.resize(d.Samples());
      raw::Uncompress(d.ADCs(), buf, d.GetPedestal(), d.Compression());
      std::memcpy(adc + ch * fNticks, buf.data(), sizeof(short) * buf.size());
      ped[ch] = d.GetPedestal(); sig[ch] = d.GetSigma(); present[ch] = 1;
    }
  }

  // ---- recob::Wire (deconvolved) -----------------------------------------
  long long loadWires(std::string label, std::string inst, std::string proc) {
    fWire = fEv.getValidHandle<std::vector<recob::Wire>>(art::InputTag(label, inst, proc)).product();
    fWireNch = 0; fWireNticks = 0;
    for (auto const& w : *fWire) {
      if (w.Channel() + 1 > fWireNch) fWireNch = w.Channel() + 1;
      if (w.NSignal() > fWireNticks) fWireNticks = w.NSignal();
    }
    return fWire->size();
  }
  unsigned wireNChannels() const { return fWireNch; }
  unsigned wireNTicks() const { return fWireNticks; }
  // signal: float32 [nch*nticks] (caller zero-initialises); ROIs are written in place
  void fillWires(ULong64_t sig_) const {
    float* sig = (float*)sig_;
    for (auto const& w : *fWire) {
      float* row = sig + (size_t)w.Channel() * fWireNticks;
      for (auto const& r : w.SignalROI().get_ranges()) {
        size_t t = r.begin_index();
        for (float v : r) row[t++] = v;
      }
    }
  }

  // ---- sim::SimChannel ----------------------------------------------------
  // returns number of IDEs (rows)
  long long loadSimChannels(std::string label, std::string inst, std::string proc) {
    fSC = fEv.getValidHandle<std::vector<sim::SimChannel>>(art::InputTag(label, inst, proc)).product();
    long long n = 0;
    for (auto const& s : *fSC) for (auto const& p : s.TDCIDEMap()) n += p.second.size();
    return n;
  }
  long long nSimChannels() const { return fSC->size(); }
  // channel,tdc,track_id: int32 [n]; nelec,energy,x,y,z: float32 [n]
  void fillSimChannels(ULong64_t ch_, ULong64_t tdc_, ULong64_t tid_, ULong64_t ne_, ULong64_t en_,
                       ULong64_t x_, ULong64_t y_, ULong64_t z_) const {
    int* ch = (int*)ch_; int* tdc = (int*)tdc_; int* tid = (int*)tid_;
    float* ne = (float*)ne_; float* en = (float*)en_; float* x = (float*)x_; float* y = (float*)y_; float* z = (float*)z_;
    // order rows by channel number (the product is not guaranteed sorted)
    std::map<unsigned, const sim::SimChannel*> ordered;
    for (auto const& s : *fSC) ordered[s.Channel()] = &s;
    size_t i = 0;
    for (auto const& kv : ordered)
      for (auto const& p : kv.second->TDCIDEMap())
        for (auto const& ide : p.second) {
          ch[i] = kv.first; tdc[i] = p.first; tid[i] = ide.trackID;
          ne[i] = ide.numElectrons; en[i] = ide.energy; x[i] = ide.x; y[i] = ide.y; z[i] = ide.z;
          ++i;
        }
  }

  // ---- sim::SimEnergyDeposit ---------------------------------------------
  long long loadEnergyDeposits(std::string label, std::string inst, std::string proc) {
    fSED = fEv.getValidHandle<std::vector<sim::SimEnergyDeposit>>(art::InputTag(label, inst, proc)).product();
    return fSED->size();
  }
  // track_id,pdg,nelec,nphot: int32 [n]; energy: float32 [n]; start,end: float32 [n*3]; t: float64 [n*2]
  void fillEnergyDeposits(ULong64_t tid_, ULong64_t pdg_, ULong64_t ne_, ULong64_t nph_, ULong64_t en_,
                          ULong64_t start_, ULong64_t end_, ULong64_t t_) const {
    int* tid = (int*)tid_; int* pdg = (int*)pdg_; int* ne = (int*)ne_; int* nph = (int*)nph_;
    float* en = (float*)en_; float* st = (float*)start_; float* ed = (float*)end_; double* t = (double*)t_;
    size_t i = 0;
    for (auto const& e : *fSED) {
      tid[i] = e.TrackID(); pdg[i] = e.PdgCode(); ne[i] = e.NumElectrons(); nph[i] = e.NumPhotons();
      en[i] = e.Energy();
      st[3*i] = e.StartX(); st[3*i+1] = e.StartY(); st[3*i+2] = e.StartZ();
      ed[3*i] = e.EndX();   ed[3*i+1] = e.EndY();   ed[3*i+2] = e.EndZ();
      t[2*i] = e.StartT();  t[2*i+1] = e.EndT();
      ++i;
    }
  }

  // ---- std::vector<int> (WireCell channel masks: simnfspl1 badchannels / badmasks)
  // returns the number of ints, or -1 if the product is not in the file
  long long loadIntVector(std::string label, std::string inst, std::string proc) {
    fInts = nullptr;
    try {
      fInts = fEv.getValidHandle<std::vector<int>>(art::InputTag(label, inst, proc)).product();
    } catch (...) { return -1; }
    return fInts->size();
  }
  void fillIntVector(ULong64_t out_) const {
    if (fInts && !fInts->empty()) std::memcpy((int*)out_, fInts->data(), sizeof(int) * fInts->size());
  }

  // ---- simb::MCParticle (+ MCTruth origin through the largeant Assns) ------
  long long loadParticles(std::string label, std::string inst, std::string proc) {
    art::InputTag tag(label, inst, proc);
    fMCP = fEv.getValidHandle<std::vector<simb::MCParticle>>(tag).product();
    fOrigin.assign(fMCP->size(), 0); fTruthIdx.assign(fMCP->size(), -1);
    typedef art::Assns<simb::MCTruth, simb::MCParticle, sim::GeneratedParticleInfo> assn_t;
    try {
      auto const& assn = *fEv.getValidHandle<assn_t>(tag);
      std::map<std::pair<art::ProductID, size_t>, int> truthIndex;
      for (auto const& pr : assn) {
        const size_t ip = pr.second.key();
        if (ip >= fMCP->size()) continue;
        fOrigin[ip] = (int)pr.first->Origin();
        auto key = std::make_pair(pr.first.id(), (size_t)pr.first.key());
        auto it = truthIndex.find(key);
        if (it == truthIndex.end()) it = truthIndex.insert(std::make_pair(key, (int)truthIndex.size())).first;
        fTruthIdx[ip] = it->second;
      }
      fHaveOrigin = true;
    } catch (...) { fHaveOrigin = false; }
    fProcNames.clear(); fProcCode.clear();
    return fMCP->size();
  }
  bool haveOrigin() const { return fHaveOrigin; }
  // track_id,pdg,mother,ancestor,status,process,origin,truth_index: int32 [n]
  // energy(start E, GeV),mass: float32 [n]; start,end: float32 [n*3] (cm); mom: float32 [n*3] (GeV); t: float64 [n*2] (ns)
  void fillParticles(ULong64_t tid_, ULong64_t pdg_, ULong64_t mother_, ULong64_t anc_, ULong64_t status_,
                     ULong64_t proc_, ULong64_t origin_, ULong64_t tidx_, ULong64_t en_, ULong64_t mass_,
                     ULong64_t start_, ULong64_t end_, ULong64_t mom_, ULong64_t t_) {
    int* tid = (int*)tid_; int* pdg = (int*)pdg_; int* mother = (int*)mother_; int* anc = (int*)anc_;
    int* status = (int*)status_; int* proc = (int*)proc_; int* origin = (int*)origin_; int* tidx = (int*)tidx_;
    float* en = (float*)en_; float* mass = (float*)mass_;
    float* st = (float*)start_; float* ed = (float*)end_; float* mom = (float*)mom_; double* t = (double*)t_;
    std::map<int, int> motherOf;
    for (auto const& p : *fMCP) motherOf[p.TrackId()] = p.Mother();
    size_t i = 0;
    for (auto const& p : *fMCP) {
      tid[i] = p.TrackId(); pdg[i] = p.PdgCode(); mother[i] = p.Mother(); status[i] = p.StatusCode();
      int a = p.TrackId();
      for (int guard = 0; guard < 100000; ++guard) {
        auto it = motherOf.find(a);
        if (it == motherOf.end() || it->second <= 0 || motherOf.find(it->second) == motherOf.end()) break;
        a = it->second;
      }
      anc[i] = a;
      auto pit = fProcCode.find(p.Process());
      if (pit == fProcCode.end()) {
        pit = fProcCode.insert(std::make_pair(p.Process(), (int)fProcNames.size())).first;
        fProcNames.push_back(p.Process());
      }
      proc[i] = pit->second;
      origin[i] = fOrigin[i]; tidx[i] = fTruthIdx[i];
      en[i] = p.E(); mass[i] = p.Mass();
      st[3*i] = p.Vx(); st[3*i+1] = p.Vy(); st[3*i+2] = p.Vz();
      ed[3*i] = p.EndX(); ed[3*i+1] = p.EndY(); ed[3*i+2] = p.EndZ();
      mom[3*i] = p.Px(); mom[3*i+1] = p.Py(); mom[3*i+2] = p.Pz();
      t[2*i] = p.T(); t[2*i+1] = p.EndT();
      ++i;
    }
  }
  // ';'-joined process names; index = value in the "process" column
  std::string processNames() const {
    std::string s;
    for (size_t i = 0; i < fProcNames.size(); ++i) { if (i) s += ";"; s += fProcNames[i]; }
    return s;
  }

private:
  void clear() { fRD = nullptr; fWire = nullptr; fSC = nullptr; fSED = nullptr; fMCP = nullptr; fInts = nullptr; }
  gallery::Event fEv;
  const std::vector<raw::RawDigit>* fRD = nullptr;
  const std::vector<recob::Wire>* fWire = nullptr;
  const std::vector<sim::SimChannel>* fSC = nullptr;
  const std::vector<sim::SimEnergyDeposit>* fSED = nullptr;
  const std::vector<simb::MCParticle>* fMCP = nullptr;
  const std::vector<int>* fInts = nullptr;
  unsigned fNch = 0, fNticks = 0, fWireNch = 0, fWireNticks = 0;
  std::vector<int> fOrigin, fTruthIdx;
  bool fHaveOrigin = false;
  std::vector<std::string> fProcNames;
  std::map<std::string, int> fProcCode;
};
